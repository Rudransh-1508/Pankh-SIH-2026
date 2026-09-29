import pytest
from sqlalchemy import select, update

from app.db import get_sessionmaker
from app.models import CoverageRun
from app.outreach.messages import family_message, school_message


@pytest.fixture
async def run(client, official):
    ministry = await official("ministry")
    response = await client.post("/v1/ministry/coverage/runs", headers=ministry)
    assert response.status_code == 201, response.text
    return ministry


async def _busiest_district(client, ministry) -> tuple[str, str]:
    coverage = (await client.get("/v1/ministry/coverage", headers=ministry)).json()
    return max(
        (
            (s["state"], d["district"], d["unreached"])
            for s in coverage["states"]
            for d in s["districts"]
        ),
        key=lambda x: x[2],
    )[:2]


def test_messages_name_the_ministry_and_say_it_is_free():
    text = family_message("en", "Sunita Murmu", ["Pre-Matric", "NMMSS", "Pre-Matric"])
    assert text.startswith("Pankh, Ministry of Tribal Affairs: Sunita may qualify for the ")
    assert "Pre-Matric or NMMSS" in text
    assert "Applying is free" in text and "Nobody will ask you for money or an OTP" in text
    hindi = school_message("hi", "GHS Kanke", 3, ["Pre-Matric"], "https://x")
    assert "GHS Kanke के 3 अनुसूचित जनजाति विद्यार्थी Pre-Matric" in hindi


async def test_a_district_drafts_previews_and_sends_to_schools(client, official, sms, run):
    state, district = await _busiest_district(client, run)
    officer = await official("district", state, district)

    draft = await client.post(
        "/v1/outreach/campaigns",
        headers=officer,
        # A district official cannot reach outside their district, whatever they ask for.
        json={"channel": "school", "state": "Elsewhere", "district": "Nowhere"},
    )
    assert draft.status_code == 201, draft.text
    body = draft.json()
    assert (body["state"], body["district"]) == (state, district)
    assert body["status"] == "draft"
    assert body["students"] > 0 and body["schools"] > 0
    assert body["delivery"] == {"pending": body["students"]}
    assert body["preview"][0]["text"].startswith("Pankh, Ministry of Tribal Affairs:")
    assert "/v1/outreach/l/" in body["preview"][0]["text"]
    assert sms.texts == []  # nothing goes out before approval

    sent = await client.post(f"/v1/outreach/campaigns/{body['id']}/send", headers=officer)
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "sent"
    assert sent.json()["delivery"] == {"sent": body["students"]}
    assert len(sms.texts) == body["schools"]
    assert all(phone.startswith("+9179") for phone, _ in sms.texts)
    again = await client.post(f"/v1/outreach/campaigns/{body['id']}/send", headers=officer)
    assert again.status_code == 409

    # The school opens its list from the message, without signing in.
    link = sms.texts[0][1].split("http://localhost:8000")[1].split(" ")[0]
    page = await client.get(link)
    assert page.status_code == 200
    assert "Students who may qualify for a scholarship" in page.text
    assert "<td>" in page.text
    assert (await client.get(link + "x")).status_code == 404
    # Short enough that the English message fits in two SMS segments.
    assert all(len(text) <= 306 for _, text in sms.texts)


async def test_families_are_told_in_hindi_and_not_messaged_twice(client, official, sms, run):
    state, district = await _busiest_district(client, run)
    officer = await official("district", state, district)
    draft = (
        await client.post(
            "/v1/outreach/campaigns",
            headers=officer,
            json={"channel": "family", "language": "hi"},
        )
    ).json()
    assert "छात्रवृत्ति मिल सकती है" in draft["preview"][0]["text"]
    await client.post(f"/v1/outreach/campaigns/{draft['id']}/send", headers=officer)
    assert len(sms.texts) == draft["students"]
    assert all("OTP नहीं माँगेगा" in text for _, text in sms.texts)

    repeat = await client.post(
        "/v1/outreach/campaigns", headers=officer, json={"channel": "family"}
    )
    assert repeat.status_code == 409
    assert "messaged recently" in repeat.json()["detail"]


async def test_results_count_students_who_applied_since(client, official, sms, run):
    state, district = await _busiest_district(client, run)
    officer = await official("district", state, district)
    draft = (
        await client.post("/v1/outreach/campaigns", headers=officer, json={"channel": "school"})
    ).json()
    await client.post(f"/v1/outreach/campaigns/{draft['id']}/send", headers=officer)
    assert (await client.get(f"/v1/outreach/campaigns/{draft['id']}", headers=officer)).json()[
        "applied_since"
    ] is None

    # A later coverage run in which two of the students have since registered.
    await client.post("/v1/ministry/coverage/runs", headers=run)
    async with get_sessionmaker()() as session:
        latest = await session.scalar(
            select(CoverageRun).order_by(CoverageRun.created_at.desc()).limit(1)
        )
        in_district = [r for r in latest.unreached if r["district"] == district]
        remaining = [r for r in latest.unreached if r not in in_district[:2]]
        await session.execute(
            update(CoverageRun).where(CoverageRun.id == latest.id).values(unreached=remaining)
        )
        await session.commit()
    result = (await client.get(f"/v1/outreach/campaigns/{draft['id']}", headers=officer)).json()
    assert result["applied_since"] == 2


async def test_campaigns_are_visible_only_within_jurisdiction(client, official, run):
    state, district = await _busiest_district(client, run)
    officer = await official("district", state, district)
    draft = (
        await client.post("/v1/outreach/campaigns", headers=officer, json={"channel": "school"})
    ).json()
    other = await official("district", state, "Somewhere else")
    assert (await client.get("/v1/outreach/campaigns", headers=other)).json() == []
    assert (
        await client.get(f"/v1/outreach/campaigns/{draft['id']}", headers=other)
    ).status_code == 404
    state_officer = await official("state", state)
    assert [
        c["id"] for c in (await client.get("/v1/outreach/campaigns", headers=state_officer)).json()
    ] == [draft["id"]]
    institute = await official("institute", state, district)
    denied = await client.post(
        "/v1/outreach/campaigns", headers=institute, json={"channel": "school"}
    )
    assert denied.status_code == 403
    cancelled = await client.post(f"/v1/outreach/campaigns/{draft['id']}/cancel", headers=officer)
    assert cancelled.json()["status"] == "cancelled"
