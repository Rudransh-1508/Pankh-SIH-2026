import json

import jwt
import pytest

from app.config import get_settings
from app.main import app

TOKEN = {"X-Voice-Token": "development-voice-token"}


@pytest.fixture
def livekit():
    settings = get_settings().model_copy(
        update={
            "livekit_url": "wss://pankh-test.livekit.cloud",
            "livekit_api_key": "APItestkey",
            "livekit_api_secret": "a-test-secret-that-is-long-enough-000000000",
        }
    )
    app.dependency_overrides[get_settings] = lambda: settings
    yield settings
    app.dependency_overrides.pop(get_settings, None)


async def test_a_voice_session_sends_jago_for_this_student_only(client, auth, livekit):
    response = await client.post("/v1/me/voice/session", headers=auth, json={"language": "hi"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"] == "wss://pankh-test.livekit.cloud"
    claims = jwt.decode(body["token"], livekit.livekit_api_secret, algorithms=["HS256"])
    assert claims["video"] == {
        "roomJoin": True,
        "room": body["room"],
        "canPublish": True,
        "canSubscribe": True,
        "canPublishData": True,
    }
    (dispatch,) = claims["roomConfig"]["agents"]
    assert dispatch["agentName"] == "jago"
    me = (await client.get("/v1/me/facts", headers=auth)).json()
    assert json.loads(dispatch["metadata"])["language"] == "hi"
    assert claims["sub"].startswith("student-")
    assert me["phone"]


async def test_voice_is_unavailable_until_livekit_is_set_up(client, auth):
    response = await client.post("/v1/me/voice/session", headers=auth, json={})
    assert response.status_code == 503


async def test_the_voice_agent_gets_jagos_spoken_reply(client, auth, livekit):
    session = (await client.post("/v1/me/voice/session", headers=auth, json={})).json()
    claims = jwt.decode(session["token"], livekit.livekit_api_secret, algorithms=["HS256"])
    student_id = json.loads(claims["roomConfig"]["agents"][0]["metadata"])["student_id"]

    refused = await client.post("/v1/voice/reply", json={"student_id": student_id, "text": "hello"})
    assert refused.status_code == 401
    reply = await client.post(
        "/v1/voice/reply",
        headers=TOKEN,
        json={"student_id": student_id, "text": "Which scholarships can I get?"},
    )
    assert reply.status_code == 200
    assert reply.json()["text"]
    assert "₹" not in reply.json()["text"]
    # The spoken conversation is part of the Student's JAGO history.
    history = (await client.get("/v1/me/jago", headers=auth)).json()
    assert history[0]["text"] == "Which scholarships can I get?"
