from app.academic_year import current_academic_year, label

ELIGIBLE_POST_MATRIC = {
    "is_scheduled_tribe": True,
    "education_level": "undergraduate",
    "studies_abroad": False,
    "institution_recognised": True,
    "family_income": 240000,
    "repeating_stage_in_other_subject": False,
    "admitted_to_top_class_institute": False,
    "current_mota_award": "none",
    "holds_other_scholarship": False,
}


async def test_anonymous_check_orders_eligible_schemes_first(client):
    response = await client.post(
        "/v1/eligibility", params={"academic_year": 2026}, json={"facts": ELIGIBLE_POST_MATRIC}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["academic_year_label"] == "2026-27"
    first = body["schemes"][0]
    assert (first["scheme"]["id"], first["status"]) == ("post_matric", "eligible")
    assert [s["status"] for s in body["schemes"]].count("eligible") == 1
    income = next(r for r in first["rules"] if r["id"] == "post_matric.income_within_ceiling")
    assert income["title"] == "Family income is at most ₹2,50,000 a year"
    assert income["citation"]["source_id"] == "post-matric-regulations"


async def test_next_facts_come_from_undecided_schemes(client):
    body = (
        await client.post("/v1/eligibility", json={"facts": {"is_scheduled_tribe": True}})
    ).json()
    assert body["next_facts"]
    assert all(s["status"] == "needs_information" for s in body["schemes"])


async def test_bad_input_is_422(client):
    bad_fact = await client.post("/v1/eligibility", json={"facts": {"family_income": "x"}})
    assert bad_fact.status_code == 422
    too_early = await client.post(
        "/v1/eligibility", params={"academic_year": 2019}, json={"facts": {}}
    )
    assert too_early.status_code == 422


async def test_defaults_to_the_current_academic_year(client):
    body = (await client.post("/v1/eligibility", json={"facts": {}})).json()
    assert body["academic_year"] == current_academic_year()
    assert body["academic_year_label"] == label(current_academic_year())


async def test_my_eligibility_uses_stored_facts(client, auth):
    await client.patch("/v1/me/facts", headers=auth, json={"facts": ELIGIBLE_POST_MATRIC})
    body = (
        await client.get("/v1/me/eligibility", headers=auth, params={"academic_year": 2026})
    ).json()
    assert body["schemes"][0]["scheme"]["id"] == "post_matric"
    assert body["schemes"][0]["status"] == "eligible"
