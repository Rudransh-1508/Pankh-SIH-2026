from sqlalchemy import func, select

from app.db import get_sessionmaker
from app.models import FactRecord


async def test_facts_are_recorded_and_read_back(client, auth, phone):
    response = await client.patch(
        "/v1/me/facts",
        headers=auth,
        json={
            "facts": {
                "is_scheduled_tribe": True,
                "family_income": 180000,
                "date_of_birth": "2010-05-04",
            }
        },
    )
    assert response.status_code == 200
    body = (await client.get("/v1/me/facts", headers=auth)).json()
    assert body == {
        "phone": phone,
        "facts": {
            "is_scheduled_tribe": True,
            "family_income": 180000.0,
            "date_of_birth": "2010-05-04",
        },
    }


async def test_newest_value_wins_and_history_is_kept(client, auth):
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 300000}})
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 240000}})
    body = (await client.get("/v1/me/facts", headers=auth)).json()
    assert body["facts"] == {"family_income": 240000.0}
    async with get_sessionmaker()() as session:
        count = await session.scalar(select(func.count()).select_from(FactRecord))
    assert count == 2


async def test_null_withdraws_a_fact(client, auth):
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": 300000}})
    await client.patch("/v1/me/facts", headers=auth, json={"facts": {"family_income": None}})
    body = (await client.get("/v1/me/facts", headers=auth)).json()
    assert body["facts"] == {}


async def test_invalid_facts_are_rejected_without_storing_anything(client, auth):
    for facts in [
        {"family_income": "a lot"},
        {"caste": "ST"},
        {"is_scheduled_tribe": True, "caste": None},
    ]:
        response = await client.patch("/v1/me/facts", headers=auth, json={"facts": facts})
        assert response.status_code == 422, facts
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(func.count()).select_from(FactRecord)) == 0
