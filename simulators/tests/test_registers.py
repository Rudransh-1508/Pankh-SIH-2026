import pytest
from httpx import ASGITransport, AsyncClient
from pankh_simulators.app import app
from pankh_simulators.population import population
from pankh_simulators.registers import API_KEY, caste_certificate_number

KEY = {"X-API-Key": API_KEY}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://sim") as client:
        yield client


async def test_registers_need_an_api_key(client):
    assert (await client.get("/aishe/institutions/x")).status_code == 401


async def test_edistrict_verifies_caste_certificates(client):
    person = next(p for p in population().people if p.has_caste_certificate)
    number = caste_certificate_number(person)
    body = (
        await client.get(f"/edistrict/{person.state.code}/certificates/{number}", headers=KEY)
    ).json()
    assert body["status"] == "VALID"
    assert body["holder_name"] == person.caste_certificate_spelling
    assert (
        await client.get(f"/edistrict/{person.state.code}/certificates/NOPE", headers=KEY)
    ).status_code == 404


async def test_aishe_and_udise_lookups(client):
    institutions = population().institutions.values()
    college = next(i for i in institutions if i.kind == "college")
    school = next(i for i in institutions if i.kind == "school")
    assert (await client.get(f"/aishe/institutions/{college.code}", headers=KEY)).json()[
        "name"
    ] == college.name
    assert (await client.get(f"/udise/schools/{school.code}", headers=KEY)).json()[
        "recognised"
    ] == school.recognised
    assert (await client.get(f"/aishe/institutions/{school.code}", headers=KEY)).status_code == 404


async def test_udise_roster_filters_scheduled_tribe_students(client):
    body = (
        await client.get(
            "/udise/students", params={"social_category": "ST", "limit": 50}, headers=KEY
        )
    ).json()
    assert body["total"] > 0
    assert all(item["social_category"] == "ST" for item in body["items"])


async def test_net_results_and_bank_seeding(client):
    person = next(p for p in population().people if p.net_roll_number)
    result = (await client.get(f"/nta/net-results/{person.net_roll_number}", headers=KEY)).json()
    assert result["qualified"] == (person.net_result is not None)
    seeding = await client.post(
        "/npci/aadhaar-seeding", json={"reference_key": person.uid_token}, headers=KEY
    )
    assert seeding.json()["seeded"] == person.bank_seeded


def test_population_is_the_same_every_time():
    assert population().people[41] == population.__wrapped__().people[41]
