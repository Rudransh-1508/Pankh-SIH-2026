from pankh_simulators.population import population


async def _linked(client, sign_in, link_digilocker, person_id):
    person = population().by_id(person_id)
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    await link_digilocker(auth, person)
    return person, auth


async def test_a_stale_income_certificate_offers_a_letter_to_the_tehsildar(
    client, sign_in, link_digilocker
):
    # P00084 has an old income certificate in DigiLocker.
    person, auth = await _linked(client, sign_in, link_digilocker, "P00084")
    issues = (await client.get("/v1/me/verification", headers=auth)).json()["exceptions"]
    (stale,) = [i for i in issues if i["kind"] == "stale_document"]
    assert stale["letter"] == "income_certificate"

    letter = (await client.get("/v1/me/letters/income_certificate", headers=auth)).json()
    assert letter["to"] == f"The Tehsildar,\nTehsil office, {person.district}, {person.state.name}"
    assert "financial year 2025-26" in letter["subject"]
    assert letter["body"].startswith(f"I, {person.name}, resident of {person.district}")
    assert f"+91{person.phone}" in letter["closing"]

    hindi = (await client.get("/v1/me/letters/income_certificate?language=hi", headers=auth)).json()
    assert hindi["subject"] == "वित्तीय वर्ष 2025-26 का आय प्रमाण पत्र जारी करने हेतु आवेदन"


async def test_a_failed_payment_points_to_the_bank_letter(client, sign_in, link_digilocker):
    # P00015's last instalment failed because the account is not seeded with Aadhaar.
    _, auth = await _linked(client, sign_in, link_digilocker, "P00015")
    applications = (await client.get("/v1/me/applications", headers=auth)).json()["applications"]
    problems = [i["problem"] for a in applications for i in a["instalments"] if i["problem"]]
    assert problems and problems[-1]["letter"] == "bank_seeding"
    letter = (await client.get("/v1/me/letters/bank_seeding", headers=auth)).json()
    assert "seed my Aadhaar with this account" in letter["body"]
    assert "________" in letter["body"]  # the account number is left for the Student to fill


async def test_letters_are_private_and_known(client, auth):
    assert (await client.get("/v1/me/letters/nonsense", headers=auth)).status_code == 404
    other = await client.get(
        "/v1/me/letters/certificate_correction",
        headers=auth,
        params={"issue": "00000000-0000-0000-0000-000000000000"},
    )
    assert other.status_code == 404
    assert (await client.get("/v1/me/letters/bank_seeding")).status_code == 401
