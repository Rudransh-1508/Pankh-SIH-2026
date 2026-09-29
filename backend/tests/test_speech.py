import base64
import json

import httpx
import pytest

from app.config import get_settings
from app.main import app
from app.phone.ivr import spoken
from app.sources.http import get_source_http

WAV = b"RIFF-test-audio"


@pytest.fixture
def sarvam():
    """Sarvam answered in-process; everything else still goes to the simulators."""
    from pankh_simulators.app import app as simulator_app

    requests: list[dict] = []
    simulators = httpx.ASGITransport(app=simulator_app)

    async def route(request: httpx.Request) -> httpx.Response:
        if request.url.host != "api.sarvam.ai":
            return await simulators.handle_async_request(request)
        assert request.headers["api-subscription-key"] == "sarvam-test-key"
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"audios": [base64.b64encode(WAV).decode()]})

    async def source_http():
        async with httpx.AsyncClient(transport=httpx.MockTransport(route)) as http:
            yield http

    settings = get_settings().model_copy(update={"sarvam_api_key": "sarvam-test-key"})
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_source_http] = source_http
    yield requests
    app.dependency_overrides.pop(get_settings, None)


async def jago_said(client, auth, language="en") -> str:
    response = await client.post(
        "/v1/me/jago", headers=auth, json={"message": "hello", "language": language}
    )
    return response.json()["text"]


async def test_a_reply_is_read_in_jagos_voice(client, auth, sarvam):
    text = await jago_said(client, auth, "hi")
    response = await client.post(
        "/v1/me/jago/speech", headers=auth, json={"text": text, "language": "hi"}
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == WAV
    (sent,) = sarvam
    assert sent["target_language_code"] == "hi-IN"
    assert (sent["model"], sent["speaker"]) == ("bulbul:v3", "shubh")


async def test_only_what_jago_said_to_this_student_can_be_read(client, auth, sarvam):
    response = await client.post(
        "/v1/me/jago/speech", headers=auth, json={"text": "Read this for free", "language": "en"}
    )
    assert response.status_code == 404
    assert sarvam == []


async def test_speech_is_unavailable_until_sarvam_is_set_up(client, auth):
    text = await jago_said(client, auth)
    response = await client.post(
        "/v1/me/jago/speech", headers=auth, json={"text": text, "language": "en"}
    )
    assert response.status_code == 503


def test_markdown_is_not_read_aloud():
    assert spoken("You can get **Post-Matric** for ₹1,000.", "en") == (
        "You can get Post-Matric for rupees 1,000."
    )
