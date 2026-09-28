import base64
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from pankh_simulators.app import app as simulator_app
from pankh_simulators.population import Person, population

from app.verification.names import match_names
from app.verification.proofs import verify


async def link_digilocker(client: AsyncClient, auth: dict, person: Person) -> dict:
    """Walk the whole DigiLocker flow as the phone and the Student would."""
    start = await client.post("/v1/me/digilocker/start", headers=auth)
    assert start.status_code == 200, start.text
    query = parse_qs(urlparse(start.json()["authorization_url"]).query)
    async with AsyncClient(
        transport=ASGITransport(app=simulator_app), base_url="http://sim"
    ) as sim:
        consent = await sim.post(
            "/digilocker/public/oauth2/1/authorize",
            data={
                "client_id": query["client_id"][0],
                "redirect_uri": query["redirect_uri"][0],
                "state": query["state"][0],
                "code_challenge": query["code_challenge"][0],
                "person_id": person.id,
            },
        )
    callback = parse_qs(urlparse(consent.headers["location"]).query)
    complete = await client.post(
        "/v1/me/digilocker/complete",
        headers=auth,
        json={"code": callback["code"][0], "state": callback["state"][0]},
    )
    assert complete.status_code == 200, complete.text
    return complete.json()


def find_person(**conditions) -> Person:
    def ok(p: Person) -> bool:
        exact = match_names(p.caste_certificate_spelling, p.name).is_match
        checks = {
            "caste_certificate": p.has_caste_certificate,
            "income_certificate": p.has_income_certificate,
            "stale_income": p.stale_income_certificate,
            "clean_spelling": exact,
            "net": p.net_result is not None,
        }
        return all(checks[key] == value for key, value in conditions.items())

    return next(p for p in population().people if ok(p))


async def test_linking_digilocker_proves_facts_anyone_can_check(client, auth):
    person = find_person(
        caste_certificate=True, income_certificate=True, stale_income=False, clean_spelling=True
    )
    linked = await link_digilocker(client, auth, person)

    proven = {proof["fact_name"] for proof in linked["proofs"]}
    assert {"is_scheduled_tribe", "family_income", "date_of_birth"} <= proven
    assert linked["exceptions"] == []

    status = (await client.get("/v1/me/verification", headers=auth)).json()
    assert status["identity"]["name"] == person.name
    assert status["facts"]["is_scheduled_tribe"] == {
        "value": True,
        "source": "digilocker",
        "verified": True,
        "proof_id": status["facts"]["is_scheduled_tribe"]["proof_id"],
    }
    assert status["facts"]["family_income"]["value"] == person.family_income
    assert {d["doctype"] for d in status["documents"]} >= {"ADHAR", "CSCER", "INCER"}

    proof_id = status["facts"]["is_scheduled_tribe"]["proof_id"]
    signed = (await client.get(f"/v1/proofs/{proof_id}")).json()
    key = (await client.get("/v1/proofs/keys")).json()[0]
    public = base64.urlsafe_b64decode(key["x"] + "=")
    assert signed["key_id"] == key["kid"]
    assert verify(public, signed["payload"], signed["signature"])
    tampered = signed["payload"] | {"value": False}
    assert not verify(public, tampered, signed["signature"])


async def test_verified_facts_feed_eligibility(client, auth):
    person = find_person(
        caste_certificate=True, income_certificate=True, stale_income=False, clean_spelling=True
    )
    await link_digilocker(client, auth, person)
    body = (await client.get("/v1/me/eligibility", headers=auth)).json()
    rules = {r["id"]: r for s in body["schemes"] for r in s["rules"]}
    assert rules["post_matric.scheduled_tribe"]["outcome"] == "pass"


async def test_a_name_that_does_not_match_goes_to_review_without_blocking(client, auth):
    person = find_person(caste_certificate=True, clean_spelling=False)
    linked = await link_digilocker(client, auth, person)
    exception = next(e for e in linked["exceptions"] if e["fact_name"] == "is_scheduled_tribe")
    assert exception["kind"] == "name_mismatch"
    assert person.caste_certificate_spelling in exception["message"]
    status = (await client.get("/v1/me/verification", headers=auth)).json()
    # The Fact is still recorded, so eligibility can go ahead while a Reviewer looks.
    assert status["facts"]["is_scheduled_tribe"]["verified"] is False
    assert status["facts"]["is_scheduled_tribe"]["value"] is True


async def test_a_stale_income_certificate_is_flagged_with_a_fix(client, auth):
    person = find_person(
        income_certificate=True, stale_income=True, clean_spelling=True, caste_certificate=True
    )
    linked = await link_digilocker(client, auth, person)
    exception = next(e for e in linked["exceptions"] if e["fact_name"] == "family_income")
    assert exception["kind"] == "stale_document"
    assert "new income certificate" in exception["remedy"]


async def test_a_certificate_outranks_a_typed_answer(client, auth):
    person = find_person(
        caste_certificate=True, income_certificate=True, stale_income=False, clean_spelling=True
    )
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 1}})
    await link_digilocker(client, auth, person)
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 2}})
    facts = (await client.get("/v1/me/facts", headers=auth)).json()["facts"]
    assert facts["family_income"] == person.family_income


async def test_one_digilocker_account_per_student(client, auth, sign_in):
    person = find_person(caste_certificate=True, clean_spelling=True)
    await link_digilocker(client, auth, person)
    other = await sign_in("+919812345678")
    other_auth = {"Authorization": f"Bearer {other['access_token']}"}
    with pytest.raises(AssertionError):
        await link_digilocker(client, other_auth, person)


async def test_institution_net_and_bank_checks(client, auth):
    person = find_person(net=True, caste_certificate=True, clean_spelling=True)
    net_before_link = await client.post(
        "/v1/me/verifications/net", headers=auth, json={"roll_number": person.net_roll_number}
    )
    assert net_before_link.status_code == 409
    await link_digilocker(client, auth, person)

    net = await client.post(
        "/v1/me/verifications/net", headers=auth, json={"roll_number": person.net_roll_number}
    )
    assert net.status_code == 200 and net.json()[0]["fact_name"] == "net_jrf_qualified"
    bank = await client.post("/v1/me/verifications/bank", headers=auth)
    assert bank.json()[0]["fact_name"] == "has_aadhaar_seeded_bank_account"

    college = next(i for i in population().institutions.values() if i.kind == "college")
    inst = await client.post(
        "/v1/me/verifications/institution", headers=auth, json={"code": college.code}
    )
    assert {p["fact_name"] for p in inst.json()} == {
        "institution_recognised",
        "institution_eligible_for_fellowship",
    }
    unknown = await client.post(
        "/v1/me/verifications/institution", headers=auth, json={"code": "NOPE"}
    )
    assert unknown.status_code == 409


async def test_expired_or_foreign_digilocker_state_is_refused(client, auth):
    response = await client.post(
        "/v1/me/digilocker/complete", headers=auth, json={"code": "x", "state": "never-started"}
    )
    assert response.status_code == 409
