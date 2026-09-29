import uuid
from datetime import date, timedelta

from pankh_simulators.population import population
from pankh_simulators.scholarship_systems import nsp_applications
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.applications.tracker import from_nsp
from app.chasing import workflows
from app.chasing.planner import OpenIssue, plan


def _nsp(status: str, days_ago: int, remark: str | None = None, payments=()) -> dict:
    on = (date.today() - timedelta(days=days_ago)).isoformat()
    return {
        "application_id": "NSP1",
        "scheme_code": "POST-MATRIC-ST",
        "academic_year": "2026-27",
        "status": status,
        "defect_remarks": remark,
        "history": [{"status": status, "on": on}],
        "sanctioned_amount": None,
        "payments": list(payments),
    }


def test_stalled_applications_become_office_proposals():
    (proposal,) = plan([from_nsp(_nsp("Verified by Institute", 45))], [], date.today())
    assert (proposal.audience, proposal.kind, proposal.level) == (
        "office",
        "stalled_application",
        "district",
    )
    assert "45 days" in proposal.message
    assert plan([from_nsp(_nsp("Verified by Institute", 10))], [], date.today()) == []


def test_students_hear_about_their_own_deficiencies_and_payments():
    failed = {
        "instalment": 1,
        "amount": 9250,
        "pfms_status": "Failed",
        "failure_code": "ACNS",
        "failure_reason": "x",
        "initiated_on": None,
        "credited_on": None,
        "utr": None,
    }
    proposals = plan(
        [
            from_nsp(
                _nsp("Defective at Institute", 2, "Bonafide certificate missing institute seal.")
            ),
            from_nsp(_nsp("Payment Initiated", 5, payments=[failed]) | {"application_id": "NSP2"}),
        ],
        [OpenIssue("e1", "stale_document", "Old income certificate.", "Get a new one.")],
        date.today(),
    )
    kinds = {p.kind: p for p in proposals}
    assert set(kinds) == {"deficiency", "payment_problem", "stale_document"}
    assert all(p.audience == "student" for p in proposals)
    assert "₹9,250" in kinds["payment_problem"].message
    assert "linked with your Aadhaar" in kinds["payment_problem"].message


def _stalled_person():
    today = date.today()
    return next(
        p
        for p in population().people
        if p.mota_award in ("post_matric", "pre_matric")
        and p.has_caste_certificate
        and any(from_nsp(a).is_stalled(today) for a in nsp_applications(p))
    )


async def test_sweep_sends_student_nudges_and_proposes_office_ones(
    client, auth, link_digilocker, official, sms
):
    person = _stalled_person()
    await link_digilocker(auth, person)
    ministry = await official("ministry")
    sms.texts.clear()

    result = (await client.post("/v1/ministry/chasing/sweep", headers=ministry)).json()
    assert result["proposed_to_offices"] >= 1

    again = (await client.post("/v1/ministry/chasing/sweep", headers=ministry)).json()
    assert again["proposed_to_offices"] == 0 and again["sent_to_students"] == 0  # never twice

    proposals = (await client.get("/v1/review/nudges", headers=ministry)).json()
    stall = next(p for p in proposals if p["kind"] == "stalled_application")
    assert stall["district"] == person.district
    assert not any("waited" in text for _, text in sms.texts)  # nothing sent to offices yet


async def test_approving_sends_to_the_right_office(client, auth, link_digilocker, official, sms):
    person = _stalled_person()
    await link_digilocker(auth, person)
    ministry = await official("ministry")
    await client.post("/v1/ministry/chasing/sweep", headers=ministry)
    stall = next(
        p
        for p in (await client.get("/v1/review/nudges", headers=ministry)).json()
        if p["kind"] == "stalled_application"
    )
    level_official = await official(stall["level"], person.state.name, person.district)
    other = await official(stall["level"], "Another State", "Elsewhere")
    assert (await client.get("/v1/review/nudges", headers=other)).json() == []
    sms.texts.clear()

    decided = await client.post(
        f"/v1/review/nudges/{stall['id']}/decision",
        headers=level_official,
        json={"decision": "approve"},
    )
    assert decided.json()["status"] == "sent"
    assert len(sms.texts) == 1 and "waited" in sms.texts[0][1]
    again = await client.post(
        f"/v1/review/nudges/{stall['id']}/decision",
        headers=level_official,
        json={"decision": "dismiss"},
    )
    assert again.status_code == 409


async def test_students_see_their_reminders(client, auth, link_digilocker, official):
    person = next(
        p
        for p in population().people
        if p.mota_award == "post_matric"
        and not p.bank_seeded
        and any(a["payments"] for a in nsp_applications(p))
    )
    await link_digilocker(auth, person)
    await client.post("/v1/ministry/chasing/sweep", headers=await official("ministry"))
    reminders = (await client.get("/v1/me/nudges", headers=auth)).json()
    assert any(r["kind"] == "payment_problem" for r in reminders)


async def test_workflow_checks_daily_and_survives_long_waits():
    checks: list[str] = []

    @activity.defn(name="check_student_activity")
    async def fake_check(student_id: str) -> dict[str, int]:
        checks.append(student_id)
        return {"sent": 0, "proposed": 0}

    async with await WorkflowEnvironment.start_time_skipping() as env, Worker(
        env.client,
        task_queue="test-chasing",
        workflows=[workflows.ChaseStudent],
        activities=[fake_check],
    ):
        student_id = str(uuid.uuid4())
        handle = await env.client.start_workflow(
            workflows.ChaseStudent.run,
            student_id,
            id=f"chase-{student_id}",
            task_queue="test-chasing",
        )
        await env.sleep(timedelta(days=3, hours=1))
        assert len(checks) == 4  # now, then once each day
        await handle.terminate()
