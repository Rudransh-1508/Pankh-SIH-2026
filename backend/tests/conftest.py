import os

os.environ["PANKH_ENVIRONMENT"] = "test"
os.environ.setdefault(
    "PANKH_DATABASE_URL", "postgresql+asyncpg://pankh:pankh@localhost:5433/pankh_test"
)

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.sms import get_sms_sender
from app.db import Base, get_engine
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent
PHONE = "+919876543210"


class CapturingSmsSender:
    def __init__(self) -> None:
        self.sent: dict[str, str] = {}

    async def send_otp(self, phone: str, code: str) -> None:
        self.sent[phone] = code


@pytest.fixture(scope="session", autouse=True)
async def database() -> AsyncIterator[None]:
    """A fresh test database, built by running the real migrations."""
    async with get_engine().begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    # Alembic's async env runs its own event loop, so it goes on a worker thread.
    await asyncio.to_thread(command.upgrade, Config(str(BACKEND_DIR / "alembic.ini")), "head")
    yield
    await get_engine().dispose()


@pytest.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with get_engine().begin() as connection:
        await connection.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def sms() -> AsyncIterator[CapturingSmsSender]:
    sender = CapturingSmsSender()
    app.dependency_overrides[get_sms_sender] = lambda: sender
    yield sender
    app.dependency_overrides.pop(get_sms_sender, None)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def phone() -> str:
    return PHONE


@pytest.fixture
def sign_in(client: AsyncClient, sms: CapturingSmsSender):
    """Sign in through the real OTP flow and return the token response."""

    async def sign_in(phone: str = PHONE) -> dict:
        response = await client.post("/v1/auth/otp/request", json={"phone": phone})
        assert response.status_code == 202, response.text
        normalised = response.json()["phone"]
        response = await client.post(
            "/v1/auth/otp/verify", json={"phone": phone, "code": sms.sent[normalised]}
        )
        assert response.status_code == 200, response.text
        return response.json()

    return sign_in


@pytest.fixture
async def auth(sign_in) -> dict[str, str]:
    tokens = await sign_in()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
