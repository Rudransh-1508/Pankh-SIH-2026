import base64

import pytest
from pankh_simulators.population import Person, population

from app.verification.names import match_names
from app.verification.proofs import verify


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


async def test_linking_digilocker_proves_facts_anyone_can_check(client, auth, link_digilocker):
    person = find_person(
        caste_certificate=True, income_certificate=True, stale_income=False, clean_spelling=True
    )
    linked = await link_digilocker(auth, person)

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


async def test_verified_facts_feed_eligibility(client, auth, link_digilocker):
    person = find_person(
        caste_certificate=True, income_certificate=True, stale_income=False, clean_spelling=True
    )
    await link_digilocker(auth, person)
    body = (await client.get("/v1/me/eligibility", headers=auth)).json()
    rules = {r["id"]: r for s in body["schemes"] for r in s["rules"]}
    assert rules["post_matric.scheduled_tribe"]["outcome"] == "pass"


async def test_a_name_that_does_not_match_goes_to_review_without_blocking(
    client, auth, link_digilocker
):
    person = find_person(caste_certificate=True, clean_spelling=False)
    linked = await link_digilocker(auth, person)
    exception = next(e for e in linked["exceptions"] if e["fact_name"] == "is_scheduled_tribe")
    assert exception["kind"] == "name_mismatch"
    assert person.caste_certificate_spelling in exception["message"]
    status = (await client.get("/v1/me/verification", headers=auth)).json()
    # The Fact is still recorded, so eligibility can go ahead while a Reviewer looks.
    assert status["facts"]["is_scheduled_tribe"]["verified"] is False
    assert status["facts"]["is_scheduled_tribe"]["value"] is True


async def test_a_stale_income_certificate_is_flagged_with_a_fix(client, auth, link_digilocker):
    person = find_person(
        income_certificate=True, stale_income=True, clean_spelling=True, caste_certificate=True
    )
    linked = await link_digilocker(auth, person)
    exception = next(e for e in linked["exceptions"] if e["fact_name"] == "family_income")
    assert exception["kind"] == "stale_document"
    assert "new income certificate" in exception["remedy"]


async def test_a_certificate_outranks_a_typed_answer(client, auth, link_digilocker):
    person = find_person(
        caste_certificate=True, income_certificate=True, stale_income=False, clean_spelling=True
    )
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 1}})
    await link_digilocker(auth, person)
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 2}})
    facts = (await client.get("/v1/me/facts", headers=auth)).json()["facts"]
    assert facts["family_income"] == person.family_income


async def test_one_digilocker_account_per_student(client, auth, sign_in, link_digilocker):
    person = find_person(caste_certificate=True, clean_spelling=True)
    await link_digilocker(auth, person)
    other = await sign_in("+919812345678")
    other_auth = {"Authorization": f"Bearer {other['access_token']}"}
    with pytest.raises(AssertionError):
        await link_digilocker(other_auth, person)


async def test_institution_net_and_bank_checks(client, auth, link_digilocker):
    person = find_person(net=True, caste_certificate=True, clean_spelling=True)
    net_before_link = await client.post(
        "/v1/me/verifications/net", headers=auth, json={"roll_number": person.net_roll_number}
    )
    assert net_before_link.status_code == 409
    await link_digilocker(auth, person)

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


async def test_linking_digilocker_brings_course_and_marks_from_apaar(
    client, sign_in, link_digilocker
):
    from pankh_simulators.population import population

    # P00008 is a postgraduate student whose APAAR record holds their Bachelor's result.
    person = population().by_id("P00008")
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    linked = await link_digilocker(auth, person)
    assert "APAAR ID" in [d["name"] for d in linked["documents"]]

    facts = (await client.get("/v1/me/verification", headers=auth)).json()["facts"]
    assert facts["education_level"] == {
        "value": "postgraduate",
        "source": "apaar",
        "verified": True,
        "proof_id": facts["education_level"]["proof_id"],
    }
    assert facts["bachelors_marks_percent"]["value"] == person.bachelors_percent
    assert facts["institution_recognised"]["verified"] is True
    # JAGO does not ask for what APAAR already confirmed.
    question = (
        await client.post(
            "/v1/me/jago",
            headers=auth,
            json={"message": "which scholarships can i get", "language": "en"},
        )
    ).json()
    assert question.get("asking") not in ("education_level", "bachelors_marks_percent")
