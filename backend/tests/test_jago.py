import json

from app.jago.llm import ModelTurn, ToolCall
from app.jago.router import get_model
from app.main import app


async def say(client, auth, message, language="en"):
    response = await client.post(
        "/v1/me/jago", headers=auth, json={"message": message, "language": language}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_intake_conversation_records_answers(client, auth):
    first = await say(client, auth, "Which scholarships can I get?")
    assert first["asking"] == "is_scheduled_tribe"
    assert "Scheduled Tribe" in first["text"]
    assert first["suggestions"] == ["Yes", "No"]

    second = await say(client, auth, "haan")
    assert second["text"].startswith("Got it.")
    assert second["asking"] == "education_level"
    assert "Bachelor's degree" in second["suggestions"]

    await say(client, auth, "BA")
    facts = (await client.get("/v1/me/facts", headers=auth)).json()["facts"]
    assert facts == {"is_scheduled_tribe": True, "education_level": "undergraduate"}


async def test_speaks_hindi(client, auth):
    reply = await say(client, auth, "मुझे कौन-सी छात्रवृत्ति मिल सकती है?", language="hi")
    assert "अनुसूचित जनजाति" in reply["text"]
    assert reply["suggestions"] == ["हाँ", "नहीं"]
    after = await say(client, auth, "हाँ", language="hi")
    assert after["text"].startswith("ठीक है।")


async def test_asks_again_when_the_reply_is_not_an_answer(client, auth):
    await say(client, auth, "check my eligibility")
    reply = await say(client, auth, "hmm maybe?")
    assert "I did not catch that" in reply["text"]
    assert reply["asking"] == "is_scheduled_tribe"


async def test_explains_payments_after_digilocker(client, auth, link_digilocker):
    from pankh_simulators.population import population
    from pankh_simulators.scholarship_systems import nsp_applications

    person = next(
        p
        for p in population().people
        if p.mota_award == "post_matric"
        and not p.bank_seeded
        and any(a["payments"] for a in nsp_applications(p))
    )
    before = await say(client, auth, "has my money come?")
    assert "Link DigiLocker" in before["text"]
    await link_digilocker(auth, person)
    reply = await say(client, auth, "has my money come?")
    assert "not linked with your Aadhaar" in reply["text"]
    status = await say(client, auth, "where is my application?")
    assert "Post-Matric (NSP)" in status["text"]


async def test_scheme_questions_cite_the_guidelines(client, auth):
    reply = await say(client, auth, "tell me about top class")
    assert "₹3,000 a month" in reply["text"]
    assert reply["sources"][0]["url"].startswith("https://tribal.nic.in/")


async def test_conversation_is_kept(client, auth):
    await say(client, auth, "namaste")
    history = (await client.get("/v1/me/jago", headers=auth)).json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["text"].startswith("Namaste!")


class ScriptedModel:
    """A model that looks up eligibility, then answers from what the tool returned."""

    def __init__(self):
        self.seen: list[list[dict]] = []

    async def respond(self, messages, tools):
        self.seen.append(messages)
        if messages[-1]["role"] == "user":
            return ModelTurn(
                text=None, tool_calls=[ToolCall(id="c1", name="my_eligibility", arguments={})]
            )
        result = json.loads(messages[-1]["content"])
        undecided = sum(s["status"] == "needs_information" for s in result["schemes"])
        return ModelTurn(text=f"I need a few answers to check {undecided} schemes.")


async def test_with_a_model_answers_come_from_tools(client, auth):
    model = ScriptedModel()
    app.dependency_overrides[get_model] = lambda: model
    try:
        reply = await say(client, auth, "am I eligible for anything?")
    finally:
        app.dependency_overrides.pop(get_model, None)
    assert reply["text"] == "I need a few answers to check 8 schemes."
    # Nothing identifying the Student reaches the model: no phone number, no identifiers.
    sent = json.dumps([m for turn in model.seen for m in turn if m["role"] != "system"])
    assert "9876543210" not in sent and "uid-" not in sent and "reference_key" not in sent
    assert model.seen[0][0]["role"] == "system"
    assert "never decide eligibility" in model.seen[0][0]["content"]


async def test_what_if_questions_are_answered_from_the_planner(client, auth):
    await client.patch(
        "/v1/me/facts",
        headers=auth,
        json={
            "facts": {
                "is_scheduled_tribe": True,
                "education_level": "class_12",
                "family_income": 200000,
                "studies_abroad": False,
                "institution_recognised": True,
            }
        },
    )
    reply = await say(client, auth, "What if I get into an IIT?")
    assert reply["text"].startswith("Get admission (not through a management quota)")
    assert "Top Class" in reply["text"]
    assert any(s["title"] for s in reply["sources"])
    path = await say(client, auth, "What is my plan for the future?")
    assert path["text"].startswith("Your scholarships, stage by stage:")
    assert "Class XII" in path["text"]
    assert "What if I qualify NET?" in path["suggestions"]
