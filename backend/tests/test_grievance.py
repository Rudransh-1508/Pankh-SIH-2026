from datetime import UTC, date, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from pankh_simulators.population import population
from sqlalchemy import select

from app.applications.tracker import Application, Instalment, InstalmentStatus, Stage
from app.db import get_sessionmaker
from app.grievance.service import drafts
from app.models import AuditEvent, Consent

TODAY = date(2026, 9, 29)


def _application(**changes) -> Application:
    values = {
        "source_system": "NSP",
        "external_id": "NSPJH123",
        "scheme_id": "post_matric",
        "academic_year": "2026-27",
        "stage": Stage.UNDER_VERIFICATION,
        "status_text": "Verified by Institute",
        "waiting_on": "district",
        "since": TODAY - timedelta(days=40),
        "deficiency": None,
        "sanctioned_amount": None,
    }
    return Application(**(values | changes))


def test_a_stall_is_filed_only_after_a_reminder_has_had_time_or_twice_the_timeline():
    app = _application()
    key = "stall:NSP:NSPJH123:Verified by Institute"
    assert drafts([app], {}, set(), TODAY) == []
    recent = {key: datetime.combine(TODAY - timedelta(days=5), datetime.min.time(), UTC)}
    assert drafts([app], recent, set(), TODAY) == []
    earlier = {key: datetime.combine(TODAY - timedelta(days=20), datetime.min.time(), UTC)}
    (draft,) = drafts([app], earlier, set(), TODAY)
    assert draft.kind == "application_stalled"
    assert "even after a reminder" in draft.reason
    assert "the office was reminded on 09 September 2026" in draft.description
    very_late = _application(since=TODAY - timedelta(days=65))
    assert [d.kind for d in drafts([very_late], {}, set(), TODAY)] == ["application_stalled"]
    assert drafts([very_late], {}, {key}, TODAY) == []  # never filed twice


def test_only_payments_stuck_at_the_bank_qualify():
    def instalment(status, days, problem=None):
        return Instalment(1, 9250, status, TODAY - timedelta(days=days), None, None, problem)

    stuck = _application(
        stage=Stage.DISBURSING,
        waiting_on=None,
        instalments=[instalment(InstalmentStatus.PENDING, 45)],
    )
    (draft,) = drafts([stuck], {}, set(), TODAY)
    assert draft.kind == "payment_stuck"
    assert "Rs. 9,250" in draft.description
    fresh = _application(
        stage=Stage.DISBURSING,
        waiting_on=None,
        instalments=[instalment(InstalmentStatus.PENDING, 10)],
    )
    assert drafts([fresh], {}, set(), TODAY) == []
    # A failure with a reason is for the Student to fix (such as seeding their account).
    failed = _application(
        stage=Stage.DISBURSING,
        waiting_on=None,
        instalments=[instalment(InstalmentStatus.FAILED, 45)],
    )
    assert drafts([failed], {}, set(), TODAY) == []


async def _student(client, sign_in, link_digilocker, person_id):
    person = population().by_id(person_id)
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    await link_digilocker(auth, person)
    return auth


async def test_a_stuck_payment_is_filed_on_cpgrams_and_followed(client, sign_in, link_digilocker):
    auth = await _student(client, sign_in, link_digilocker, "P00176")
    listing = (await client.get("/v1/me/grievances", headers=auth)).json()
    assert listing["linked"] is True
    (draft,) = [d for d in listing["drafts"] if d["kind"] == "payment_stuck"]
    assert "pending at the bank" in draft["description"]

    filed = await client.post(
        "/v1/me/grievances",
        headers=auth,
        json={"key": draft["key"], "note": "My bank says nothing has arrived."},
    )
    assert filed.status_code == 201, filed.text
    grievance = filed.json()
    assert grievance["registration_number"].startswith("MOTRA/E/")
    assert grievance["status"] == "Under process"
    again = await client.post("/v1/me/grievances", headers=auth, json={"key": draft["key"]})
    assert again.status_code == 409

    # The ministry replies on CPGRAMS; the next look picks it up.
    from pankh_simulators.app import app as simulator_app

    _, _, year, serial = grievance["registration_number"].split("/")
    async with AsyncClient(
        transport=ASGITransport(app=simulator_app), base_url="http://sim"
    ) as sim:
        await sim.post(
            f"/cpgrams/grievances/{year}/{serial}/close",
            headers={"X-API-Key": "pankh-simulator-key"},
            json={"reply": "The payment was re-initiated through PFMS on 30 September."},
        )
    listing = (await client.get("/v1/me/grievances", headers=auth)).json()
    (followed,) = listing["filed"]
    assert followed["status"] == "Case closed"
    assert followed["reply"].startswith("The payment was re-initiated")
    assert followed["closed_at"] is not None
    assert all(d["key"] != draft["key"] for d in listing["drafts"])

    async with get_sessionmaker()() as session:
        assert (await session.scalars(select(Consent.source))).all().count("cpgrams") == 1
        assert "grievance.file" in (await session.scalars(select(AuditEvent.action))).all()


async def test_a_problem_the_student_can_fix_offers_no_grievance(client, sign_in, link_digilocker):
    auth = await _student(client, sign_in, link_digilocker, "P00015")
    listing = (await client.get("/v1/me/grievances", headers=auth)).json()
    assert all(d["kind"] != "payment_stuck" for d in listing["drafts"])
    refused = await client.post("/v1/me/grievances", headers=auth, json={"key": "payment:NSP:x:1"})
    assert refused.status_code == 409


async def test_without_digilocker_there_is_nothing_to_file(client, auth):
    listing = (await client.get("/v1/me/grievances", headers=auth)).json()
    assert listing == {"drafts": [], "filed": [], "linked": False}
