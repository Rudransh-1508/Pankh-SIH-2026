from pankh_simulators.population import population

CHILD_FACTS = {
    "is_scheduled_tribe": True,
    "education_level": "class_9",
    "studies_abroad": False,
    "institution_recognised": True,
    "family_income": 120000,
    "has_aadhaar_seeded_bank_account": True,
    "current_mota_award": "none",
    "holds_other_scholarship": False,
}


async def as_account(sign_in, phone):
    tokens = await sign_in(phone)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_a_guardian_follows_a_child_only_with_their_code(client, sign_in):
    child = await as_account(sign_in, "+919811111111")
    parent = await as_account(sign_in, "+919822222222")
    await client.patch("/v1/me/facts", headers=child, json={"facts": CHILD_FACTS})

    assert (await client.get("/v1/me/family", headers=parent)).json()["children"] == []
    code = (await client.post("/v1/me/family/invite", headers=child)).json()["code"]
    assert len(code) == 9 and code[4] == " "

    accepted = await client.post(
        "/v1/me/family/accept", headers=parent, json={"code": code.lower()}
    )
    assert accepted.status_code == 201
    family = (await client.get("/v1/me/family", headers=parent)).json()
    (kid,) = family["children"]
    assert kid["eligible"] == ["Pre-Matric"]
    assert kid["name"].endswith("11111")

    reused = await client.post("/v1/me/family/accept", headers=parent, json={"code": code})
    assert reused.status_code == 404  # codes work once
    child_view = (await client.get("/v1/me/family", headers=child)).json()
    assert child_view["guardians"][0]["phone"].endswith("22222")


async def test_either_side_can_stop_sharing(client, sign_in):
    child = await as_account(sign_in, "+919833333333")
    parent = await as_account(sign_in, "+919844444444")
    code = (await client.post("/v1/me/family/invite", headers=child)).json()["code"]
    link_id = (
        await client.post("/v1/me/family/accept", headers=parent, json={"code": code})
    ).json()["link_id"]
    assert (await client.delete(f"/v1/me/family/{link_id}", headers=child)).status_code == 204
    assert (await client.get("/v1/me/family", headers=parent)).json()["children"] == []
    stranger = await as_account(sign_in, "+919855555555")
    assert (await client.delete(f"/v1/me/family/{link_id}", headers=stranger)).status_code == 404


async def test_own_code_is_refused(client, sign_in):
    me = await as_account(sign_in, "+919866666666")
    code = (await client.post("/v1/me/family/invite", headers=me)).json()["code"]
    assert (
        await client.post("/v1/me/family/accept", headers=me, json={"code": code})
    ).status_code == 409


async def test_guardian_sees_applications_after_the_child_links_digilocker(
    client, sign_in, link_digilocker
):
    child = await as_account(sign_in, "+919877777777")
    parent = await as_account(sign_in, "+919888888888")
    person = next(
        p for p in population().people if p.mota_award == "pre_matric" and p.has_scholarship_record
    )
    await link_digilocker(child, person)
    code = (await client.post("/v1/me/family/invite", headers=child)).json()["code"]
    await client.post("/v1/me/family/accept", headers=parent, json={"code": code})
    (kid,) = (await client.get("/v1/me/family", headers=parent)).json()["children"]
    assert kid["name"] == person.name
    assert kid["applications"][0]["scheme"] == "Pre-Matric"
