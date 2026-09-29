"""JAGO's voice agent. LiveKit sends it to a Student's room; it listens with Sarvam speech to
text, asks the Pankh API for JAGO's reply, and speaks it with Sarvam text to speech.

It holds no knowledge of its own: every word it says comes from JAGO, grounded in the
Student's records, so talking and typing always give the same answer.

Run from voice/:  uv run python -m pankh_voice.agent dev
"""

import json
import logging
import os
from collections.abc import AsyncIterable
from pathlib import Path

import httpx
from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, llm
from livekit.plugins import sarvam, silero

# One configuration for the whole project: the backend's .env.
load_dotenv(Path(__file__).resolve().parents[2] / "backend" / ".env")
for ours, theirs in {
    "PANKH_LIVEKIT_URL": "LIVEKIT_URL",
    "PANKH_LIVEKIT_API_KEY": "LIVEKIT_API_KEY",
    "PANKH_LIVEKIT_API_SECRET": "LIVEKIT_API_SECRET",
    "PANKH_SARVAM_API_KEY": "SARVAM_API_KEY",
}.items():
    if os.environ.get(ours):
        os.environ.setdefault(theirs, os.environ[ours])

API_URL = os.environ.get("PANKH_API_URL", "http://localhost:8000").rstrip("/")
SERVICE_TOKEN = os.environ.get("PANKH_VOICE_SERVICE_TOKEN", "development-voice-token")
# The same voice the app uses to read JAGO's replies aloud (the backend's settings).
TTS_MODEL = os.environ.get("PANKH_SARVAM_TTS_MODEL", "bulbul:v3")
SPEAKER = os.environ.get("PANKH_SARVAM_SPEAKER", "shubh")

log = logging.getLogger("pankh.voice")

GREETING = {
    "en": "Namaste, I am JAGO. Ask me about your scholarships, your applications or your payments.",
    "hi": "नमस्ते, मैं JAGO हूँ। अपनी छात्रवृत्ति, आवेदन या भुगतान के बारे में पूछिए।",
    "bn": "নমস্কার, আমি JAGO। আপনার বৃত্তি, আবেদন বা টাকার বিষয়ে জিজ্ঞেস করুন।",
    "gu": "નમસ્તે, હું JAGO છું. તમારી શિષ્યવૃત્તિ, અરજી કે ચુકવણી વિશે પૂછો.",
    "mr": "नमस्कार, मी JAGO आहे. तुमची शिष्यवृत्ती, अर्ज किंवा पैशांबद्दल विचारा.",
    "or": "ନମସ୍କାର, ମୁଁ JAGO। ଆପଣଙ୍କ ଛାତ୍ରବୃତ୍ତି, ଆବେଦନ ବା ଟଙ୍କା ବିଷୟରେ ପଚାରନ୍ତୁ।",
}
UNAVAILABLE = {
    "en": "Sorry, I cannot reach Pankh right now. Please try again in a little while.",
    "hi": "माफ़ कीजिए, अभी पंख से संपर्क नहीं हो पा रहा। थोड़ी देर बाद फिर कोशिश करें।",
    "bn": "দুঃখিত, এখন পঙ্খের সঙ্গে যোগাযোগ করা যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।",
    "gu": "માફ કરશો, હમણાં પંખનો સંપર્ક થઈ શકતો નથી. થોડી વાર પછી ફરી પ્રયાસ કરો.",
    "mr": "माफ करा, सध्या पंखशी संपर्क होत नाही. थोड्या वेळाने पुन्हा प्रयत्न करा.",
    "or": "କ୍ଷମା କରନ୍ତୁ, ଏବେ ପଙ୍ଖ ସହ ଯୋଗାଯୋଗ ହୋଇପାରୁନାହିଁ। କିଛି ସମୟ ପରେ ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
}
# Sarvam's language codes; it writes Odia as "od" (ISO 639-1 "or" everywhere else).
SPEECH_LANGUAGE = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
    "or": "od-IN",
}


def last_thing_said(chat_ctx: llm.ChatContext) -> str | None:
    """The Student's latest words in the conversation."""
    for item in reversed(chat_ctx.items):
        if getattr(item, "role", None) == "user" and item.text_content:
            return item.text_content.strip()
    return None


class JagoReplies(llm.LLM):
    """Stands in for a language model. LiveKit only produces replies when a session has one,
    but JAGO's replies come from the Pankh API, in Jago.llm_node, so this is never asked."""

    @property
    def model(self) -> str:
        return "pankh-jago"

    @property
    def provider(self) -> str:
        return "pankh"

    def chat(self, **_: object) -> llm.LLMStream:
        raise NotImplementedError("JAGO's replies come from the Pankh API")


class Jago(Agent):
    def __init__(self, student_id: str, language: str, http: httpx.AsyncClient) -> None:
        super().__init__(instructions="Every reply comes from the Pankh API.")
        self.student_id = student_id
        self.language = language
        self.http = http

    async def llm_node(
        self, chat_ctx: llm.ChatContext, tools: list, model_settings
    ) -> AsyncIterable[str]:
        said = last_thing_said(chat_ctx)
        if not said:
            return
        try:
            response = await self.http.post(
                f"{API_URL}/v1/voice/reply",
                headers={"X-Voice-Token": SERVICE_TOKEN},
                json={"student_id": self.student_id, "language": self.language, "text": said},
                timeout=60,
            )
            response.raise_for_status()
            yield response.json()["text"]
        except httpx.HTTPError:
            log.exception("JAGO did not answer")
            yield UNAVAILABLE[self.language]


server = AgentServer()


@server.rtc_session(agent_name="jago")
async def conversation(ctx: JobContext) -> None:
    # The Pankh API signed this into the Student's room token; the phone cannot change it.
    details = json.loads(ctx.job.metadata or "{}")
    student_id = details["student_id"]
    language = details.get("language") if details.get("language") in GREETING else "en"
    speech = SPEECH_LANGUAGE[language]

    await ctx.connect()
    http = httpx.AsyncClient()

    async def close_http() -> None:
        await http.aclose()

    ctx.add_shutdown_callback(close_http)
    session = AgentSession(
        stt=sarvam.STT(language=speech),
        llm=JagoReplies(),
        tts=sarvam.TTS(target_language_code=speech, model=TTS_MODEL, speaker=SPEAKER),
        vad=silero.VAD.load(),
    )
    await session.start(Jago(student_id, language, http), room=ctx.room)
    session.say(GREETING[language])


if __name__ == "__main__":
    cli.run_app(server)
