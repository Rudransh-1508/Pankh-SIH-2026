"""JAGO's replies as speech, in the same Sarvam voice the voice agent uses on calls, so JAGO
sounds the same on every phone whatever voices the phone itself has installed.
"""

import base64

import httpx

from app.config import Settings

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SPEECH_LANGUAGE = {"en": "en-IN", "hi": "hi-IN"}


class SpeechUnavailable(Exception):
    pass


async def synthesise(
    settings: Settings, http: httpx.AsyncClient, text: str, language: str
) -> bytes:
    """WAV audio of the text, spoken by JAGO's voice."""
    if not settings.sarvam_api_key:
        raise SpeechUnavailable("Sarvam is not set up")
    try:
        response = await http.post(
            SARVAM_TTS_URL,
            headers={"api-subscription-key": settings.sarvam_api_key},
            json={
                "text": text,
                "target_language_code": SPEECH_LANGUAGE[language],
                "model": settings.sarvam_tts_model,
                "speaker": settings.sarvam_speaker,
            },
            timeout=30,
        )
        response.raise_for_status()
        return base64.b64decode(response.json()["audios"][0])
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
        raise SpeechUnavailable(str(error)) from error
