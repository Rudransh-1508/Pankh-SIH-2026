import re

STUDENT = "+919812345670"


def consent_code(sms, phone: str) -> str:
    (text,) = [t for p, t in sms.texts if p == phone][-1:]
    return re.search(r"\b(\d{6})\b", text).group(1)


async def approved_facilitator(client, sign_in, official):
    tokens = await sign_in("+919800000011")
    me = {"Authorization": f"Bearer {tokens['access_token']}"}
    registered = await client.post(
        "/v1/me/facilitator",
        headers=me,
        json={
            "name": "Sita Hansda",
            "organisation": "Government High School, Kanke",
            "state": "Jharkhand",
            "district": "Ranchi",
        },
    )
    assert registered.json()["status"] == "pending"
    blocked = await client.post("/v1/me/facilitator/students", headers=me, json={"phone": STUDENT})
    assert blocked.status_code == 403

    district = await official("district", "Jharkhand", "Ranchi")
    (pending,) = (await client.get("/v1/review/facilitators", headers=district)).json()
    assert pending["phone"] == "+919800000011"
    elsewhere = await official("district", "Jharkhand", "Dumka")
    assert (await client.get("/v1/review/facilitators", headers=elsewhere)).json() == []
    await client.post(
        f"/v1/review/facilitators/{pending['id']}/decision",
        headers=district,
        json={"decision": "approve"},
    )
    return me


async def test_a_facilitator_registers_a_student_with_consent_and_answers_for_them(
    client, sign_in, official, sms
):
    me = await approved_facilitator(client, sign_in, official)
    sent = await client.post("/v1/me/facilitator/students", headers=me, json={"phone": STUDENT})
    assert sent.status_code == 202
    text = [t for p, t in sms.texts if p == STUDENT][-1]
    assert "Sita Hansda of Government High School, Kanke wants to help you" in text
    assert "does not let anyone sign in as you" in text

    wrong = await client.post(
        "/v1/me/facilitator/students/confirm",
        headers=me,
        json={"phone": STUDENT, "code": "000000"},
    )
    assert wrong.status_code == 400
    linked = await client.post(
        "/v1/me/facilitator/students/confirm",
        headers=me,
        json={"phone": STUDENT, "code": consent_code(sms, STUDENT)},
    )
    assert linked.status_code == 201, linked.text
    student_id = linked.json()["student_id"]

    (helped,) = (await client.get("/v1/me/facilitator/students", headers=me)).json()
    assert helped["phone"] == "…5670"
    assert helped["next_question"]["fact"] == "is_scheduled_tribe"
    answered = await client.post(
        f"/v1/me/facilitator/students/{student_id}/answers",
        headers=me,
        json={"facts": {"is_scheduled_tribe": True, "education_level": "class_9"}},
    )
    assert answered.status_code == 200
    assert answered.json()["next_question"]["fact"] != "is_scheduled_tribe"

    # The Student later signs in: their answers are there, and they can stop the help.
    tokens = await sign_in(STUDENT)
    student = {"Authorization": f"Bearer {tokens['access_token']}"}
    facts = (await client.get("/v1/me/facts", headers=student)).json()["facts"]
    assert facts["education_level"] == "class_9"
    (helper,) = (await client.get("/v1/me/helpers", headers=student)).json()
    assert helper["name"] == "Sita Hansda"
    revoked = await client.delete(f"/v1/me/helpers/{helper['link_id']}", headers=student)
    assert revoked.status_code == 204
    assert (await client.get("/v1/me/facilitator/students", headers=me)).json() == []
    again = await client.post(
        f"/v1/me/facilitator/students/{student_id}/answers",
        headers=me,
        json={"facts": {"family_income": 100000}},
    )
    assert again.status_code == 404


async def test_a_consent_code_cannot_sign_anyone_in(client, sign_in, official, sms):
    me = await approved_facilitator(client, sign_in, official)
    await client.post("/v1/me/facilitator/students", headers=me, json={"phone": STUDENT})
    code = consent_code(sms, STUDENT)
    attempt = await client.post("/v1/auth/otp/verify", json={"phone": STUDENT, "code": code})
    assert attempt.status_code in (400, 401)


async def test_consent_codes_are_limited(client, sign_in, official, sms):
    me = await approved_facilitator(client, sign_in, official)
    for _ in range(3):
        await client.post("/v1/me/facilitator/students", headers=me, json={"phone": STUDENT})
    too_many = await client.post("/v1/me/facilitator/students", headers=me, json={"phone": STUDENT})
    assert too_many.status_code == 429
