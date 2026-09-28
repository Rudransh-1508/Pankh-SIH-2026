from pankh_simulators.population import population
from sqlalchemy import select

from app.db import get_sessionmaker
from app.models import AuditEvent
from app.verification.names import match_names


def mismatched_person():
    """Someone whose caste certificate spells their name so differently that it needs review."""
    return next(
        p
        for p in population().people
        if p.has_caste_certificate
        and not match_names(p.caste_certificate_spelling, p.name).is_match
    )


async def open_case(client, auth, link_digilocker):
    person = mismatched_person()
    await link_digilocker(auth, person)
    return person


async def test_officials_sign_in_separately_from_students(client, sms, auth, official):
    await client.post("/v1/auth/otp/request", json={"phone": "+919123456789"})
    refused = await client.post(
        "/v1/auth/otp/verify",
        json={"phone": "+919123456789", "code": sms.sent["+919123456789"], "role": "official"},
    )
    assert refused.status_code == 403
    district = await official("district", "Jharkhand", "Dumka")
    assert (await client.get("/v1/review/exceptions", headers=auth)).status_code == 401
    assert (await client.get("/v1/me/facts", headers=district)).status_code == 401


async def test_district_reviewer_sees_only_their_district(client, auth, link_digilocker, official):
    person = await open_case(client, auth, link_digilocker)
    own = await official("district", person.state.name, person.district)
    other_district = next(d for d in person.state.districts if d != person.district)
    other = await official("district", person.state.name, other_district)

    queue = (await client.get("/v1/review/exceptions", headers=own)).json()
    assert any(
        item["kind"] == "name_mismatch" and item["student_name"] == person.name for item in queue
    )
    assert (await client.get("/v1/review/exceptions", headers=other)).json() == []


async def test_confirming_a_case_issues_a_reviewer_proof(client, auth, link_digilocker, official):
    person = await open_case(client, auth, link_digilocker)
    reviewer = await official("district", person.state.name, person.district)
    item = next(
        i
        for i in (await client.get("/v1/review/exceptions", headers=reviewer)).json()
        if i["fact_name"] == "is_scheduled_tribe"
    )
    case = (await client.get(f"/v1/review/exceptions/{item['id']}", headers=reviewer)).json()
    assert case["name_comparison"]["on_document"] == person.caste_certificate_spelling

    decided = await client.post(
        f"/v1/review/exceptions/{item['id']}/decision",
        headers=reviewer,
        json={"decision": "confirm", "note": "Same person: checked school records."},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "resolved"

    status = (await client.get("/v1/me/verification", headers=auth)).json()
    assert status["facts"]["is_scheduled_tribe"]["verified"] is True
    assert status["facts"]["is_scheduled_tribe"]["source"] == "reviewer"

    again = await client.post(
        f"/v1/review/exceptions/{item['id']}/decision",
        headers=reviewer,
        json={"decision": "reject", "note": "x"},
    )
    assert again.status_code == 409
    async with get_sessionmaker()() as session:
        events = (await session.scalars(select(AuditEvent.action))).all()
    assert "case.confirm" in events


async def test_rejection_reaches_the_student_with_the_note(client, auth, link_digilocker, official):
    person = await open_case(client, auth, link_digilocker)
    reviewer = await official("district", person.state.name, person.district)
    item = (await client.get("/v1/review/exceptions", headers=reviewer)).json()[0]
    await client.post(
        f"/v1/review/exceptions/{item['id']}/decision",
        headers=reviewer,
        json={"decision": "reject", "note": "Bring your school leaving certificate to the office."},
    )
    status = (await client.get("/v1/me/verification", headers=auth)).json()
    rejected = next(e for e in status["exceptions"] if e["id"] == item["id"])
    assert rejected["status"] == "rejected"
    assert rejected["reviewer_note"] == "Bring your school leaving certificate to the office."


async def test_escalation_moves_a_case_up_a_level(client, auth, link_digilocker, official):
    person = await open_case(client, auth, link_digilocker)
    district = await official("district", person.state.name, person.district)
    state = await official("state", person.state.name)
    item = (await client.get("/v1/review/exceptions", headers=district)).json()[0]
    await client.post(
        f"/v1/review/exceptions/{item['id']}/decision",
        headers=district,
        json={"decision": "escalate", "note": "Needs the state's records."},
    )
    district_ids = {
        i["id"] for i in (await client.get("/v1/review/exceptions", headers=district)).json()
    }
    state_ids = {i["id"] for i in (await client.get("/v1/review/exceptions", headers=state)).json()}
    assert item["id"] not in district_ids
    assert item["id"] in state_ids


async def test_decisions_need_a_note(client, auth, link_digilocker, official):
    await open_case(client, auth, link_digilocker)
    ministry = await official("ministry")
    item = (await client.get("/v1/review/exceptions", headers=ministry)).json()[0]
    response = await client.post(
        f"/v1/review/exceptions/{item['id']}/decision",
        headers=ministry,
        json={"decision": "confirm", "note": "  "},
    )
    assert response.status_code == 422
