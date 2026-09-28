import pytest
from httpx import ASGITransport, AsyncClient
from pankh_simulators.app import app
from pankh_simulators.population import population
from pankh_simulators.registers import API_KEY
from pankh_simulators.scholarship_systems import nsp_applications

KEY = {"X-API-Key": API_KEY}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://sim") as client:
        yield client


def _someone(award: str):
    return next(
        p for p in population().people if p.has_scholarship_record and p.mota_award == award
    )


async def test_nsp_tracks_post_matric_applications(client):
    person = _someone("post_matric")
    body = (
        await client.get(
            "/nsp/applications", params={"reference_key": person.uid_token}, headers=KEY
        )
    ).json()
    (application,) = body["applications"]
    assert application["scheme_code"] == "POST-MATRIC-ST"
    assert application["history"][0]["status"] == "Submitted"


async def test_unseeded_accounts_fail_at_pfms(client):
    person = next(
        p
        for p in population().people
        if p.mota_award == "post_matric"
        and p.has_scholarship_record
        and not p.bank_seeded
        and any(application["payments"] for application in nsp_applications(p))
    )
    body = (
        await client.get(
            "/nsp/applications", params={"reference_key": person.uid_token}, headers=KEY
        )
    ).json()
    last = body["applications"][0]["payments"][-1]
    assert (last["pfms_status"], last["failure_code"]) == ("Failed", "ACNS")


async def test_sfmp_and_nos(client):
    fellow = _someone("nfst")
    body = (
        await client.get("/sfmp/fellows", params={"reference_key": fellow.uid_token}, headers=KEY)
    ).json()
    assert body["fellows"][0]["monthly_amount"] == 37000
    scholar = _someone("nos")
    body = (
        await client.get(
            "/nos/applications", params={"reference_key": scholar.uid_token}, headers=KEY
        )
    ).json()
    assert body["applications"][0]["course"] == "Master's"


async def test_unknown_people_are_404(client):
    response = await client.get(
        "/nsp/applications", params={"reference_key": "nobody"}, headers=KEY
    )
    assert response.status_code == 404
