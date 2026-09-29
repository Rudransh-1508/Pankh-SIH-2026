from pankh_simulators.population import population


async def _student(client, sign_in, link_digilocker, person_id: str, facts: dict) -> dict:
    person = population().by_id(person_id)
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    await link_digilocker(auth, person)
    saved = await client.patch("/v1/me/facts", headers=auth, json={"facts": facts})
    assert saved.status_code == 200, saved.text
    return auth


async def test_a_class_ix_pre_matric_holder_renews_for_class_x(client, sign_in, link_digilocker):
    # P00084 holds Pre-Matric this year, in Class IX.
    auth = await _student(
        client,
        sign_in,
        link_digilocker,
        "P00084",
        {"education_level": "class_9", "studies_abroad": False, "institution_recognised": True},
    )
    (plan,) = (await client.get("/v1/me/renewals", headers=auth)).json()
    assert plan["scheme_id"] == "pre_matric"
    assert (plan["held_year"], plan["next_year"]) == ("2026-27", "2027-28")
    assert plan["next_level"] == "class_10"
    assert plan["continuing"] is True
    assert plan["instead"] is None
    checks = {c["id"]: c for c in plan["checks"]}
    # This year's income certificate proves income only until this session ends.
    assert checks["income"]["done"] is False
    assert "income certificate for 2026-27" in checks["income"]["text"]
    assert checks["income"]["fact"] == "family_income"
    assert "Scheduled Tribe" in " ".join(plan["carried"])
    assert plan["apply_url"] == "https://scholarships.gov.in"


async def test_after_class_x_the_next_year_is_a_new_scheme(client, sign_in, link_digilocker):
    # P00023 holds Pre-Matric in Class X, which ends there: next year is Post-Matric.
    auth = await _student(
        client,
        sign_in,
        link_digilocker,
        "P00023",
        {"education_level": "class_10", "studies_abroad": False, "institution_recognised": True},
    )
    (plan,) = (await client.get("/v1/me/renewals", headers=auth)).json()
    assert plan["next_level"] == "class_11"
    assert plan["continuing"] is False
    assert plan["instead"] == "Post-Matric"
    assert "institution" in {c["id"] for c in plan["checks"]}


async def test_without_digilocker_the_answer_about_the_award_is_used(client, auth):
    await client.patch(
        "/v1/me/facts",
        headers=auth,
        json={
            "facts": {
                "is_scheduled_tribe": True,
                "education_level": "undergraduate",
                "current_mota_award": "post_matric",
            }
        },
    )
    (plan,) = (await client.get("/v1/me/renewals", headers=auth)).json()
    assert plan["scheme_id"] == "post_matric"
    assert plan["next_level"] == "undergraduate"
    assert plan["continuing"] is True


async def test_no_scheme_held_means_no_renewal(client, auth):
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"is_scheduled_tribe": True}})
    assert (await client.get("/v1/me/renewals", headers=auth)).json() == []


async def test_jago_explains_the_renewal(client, sign_in, link_digilocker):
    auth = await _student(
        client,
        sign_in,
        link_digilocker,
        "P00084",
        {"education_level": "class_9", "studies_abroad": False, "institution_recognised": True},
    )
    reply = (
        await client.post(
            "/v1/me/jago",
            headers=auth,
            json={"message": "How do I renew next year?", "language": "en"},
        )
    ).json()
    assert reply["text"].startswith("To renew Pre-Matric for 2027-28, get these ready: ")
    assert "an income certificate for 2026-27" in reply["text"]
    hindi = (
        await client.post(
            "/v1/me/jago",
            headers=auth,
            json={"message": "अगले साल नवीनीकरण कैसे होगा?", "language": "hi"},
        )
    ).json()
    assert "2026-27 का आय प्रमाण पत्र" in hindi["text"]
