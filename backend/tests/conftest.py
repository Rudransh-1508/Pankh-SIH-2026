import os

os.environ["PANKH_ENVIRONMENT"] = "test"
# Tests never reach a real language model, whatever a local .env configures.
os.environ["PANKH_BEDROCK_MODEL_ID"] = ""
os.environ["PANKH_LLM_BASE_URL"] = ""
os.environ.setdefault(
    "PANKH_DATABASE_URL", "postgresql+asyncpg://pankh:pankh@localhost:5433/pankh_test"
)

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth.sms import get_sms_sender
from app.db import Base, get_engine
from app.main import app
from app.sources.http import get_source_http

BACKEND_DIR = Path(__file__).resolve().parent.parent
PHONE = "+919876543210"


class CapturingSmsSender:
    def __init__(self) -> None:
        self.sent: dict[str, str] = {}
        self.texts: list[tuple[str, str]] = []

    async def send_otp(self, phone: str, code: str) -> None:
        self.sent[phone] = code

    async def send_text(self, phone: str, text: str) -> None:
        self.texts.append((phone, text))


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


@pytest.fixture(autouse=True)
def simulators() -> AsyncIterator[None]:
    """Source Systems and Data Sources are answered in-process by the simulators."""
    from pankh_simulators.app import app as simulator_app

    async def source_http() -> AsyncIterator[AsyncClient]:
        async with AsyncClient(transport=ASGITransport(app=simulator_app)) as http:
            yield http

    app.dependency_overrides[get_source_http] = source_http
    yield
    app.dependency_overrides.pop(get_source_http, None)


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


@pytest.fixture
def link_digilocker(client: AsyncClient):
    """Walk the whole DigiLocker flow as the phone and the Student would."""
    from pankh_simulators.app import app as simulator_app

    async def link(auth: dict, person) -> dict:
        start = await client.post("/v1/me/digilocker/start", headers=auth)
        assert start.status_code == 200, start.text
        query = parse_qs(urlparse(start.json()["authorization_url"]).query)
        transport = ASGITransport(app=simulator_app)
        async with AsyncClient(transport=transport, base_url="http://sim") as sim:
            consent = await sim.post(
                "/digilocker/public/oauth2/1/authorize",
                data={
                    "client_id": query["client_id"][0],
                    "redirect_uri": query["redirect_uri"][0],
                    "state": query["state"][0],
                    "code_challenge": query["code_challenge"][0],
                    "person_id": person.id,
                },
            )
        callback = parse_qs(urlparse(consent.headers["location"]).query)
        complete = await client.post(
            "/v1/me/digilocker/complete",
            headers=auth,
            json={"code": callback["code"][0], "state": callback["state"][0]},
        )
        assert complete.status_code == 200, complete.text
        return complete.json()

    return link


@pytest.fixture
def official(client: AsyncClient, sms: CapturingSmsSender):
    """Create an official and sign them in; returns their Authorization header."""
    from app.db import get_sessionmaker
    from app.models import Official

    counter = iter(range(100, 1000))

    async def make(level: str, state: str | None = None, district: str | None = None) -> dict:
        phone = f"+9191000{next(counter):05d}"
        async with get_sessionmaker()() as session:
            session.add(
                Official(
                    phone=phone,
                    name=f"{level} official",
                    level=level,
                    state=state,
                    district=district,
                )
            )
            await session.commit()
        await client.post("/v1/auth/otp/request", json={"phone": phone})
        response = await client.post(
            "/v1/auth/otp/verify",
            json={"phone": phone, "code": sms.sent[phone], "role": "official"},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return make
