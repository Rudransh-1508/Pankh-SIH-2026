"""Simulators for the three systems of record: NSP, SFMP (Canara Bank) and the NOS Portal.

Each speaks its own vocabulary, as the real systems do: NSP has verification levels and
"defective" applications, SFMP tracks fellows through joining reports and quarterly
continuation certificates, and the NOS Portal follows selection and embassy disbursal.
Payments go through PFMS and can fail for the reasons real payments fail.

Records are found by the Aadhaar reference key the systems share with DigiLocker.
"""

import hashlib
import random
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pankh_simulators.population import Person, population
from pankh_simulators.registers import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])

NSP_SCHEMES = {
    "pre_matric": "PRE-MATRIC-ST",
    "post_matric": "POST-MATRIC-ST",
    "top_class": "TOPCLASS-ST",
}

# The order NSP moves an application through.
NSP_STAGES = (
    "Submitted",
    "Verified by Institute",
    "Verified by District",
    "Verified by State",
    "Sanctioned",
    "Payment Initiated",
    "Paid",
)

PFMS_FAILURES = (
    ("ACNS", "Account not seeded with Aadhaar"),
    ("ACIN", "Account inactive or dormant"),
    ("NMMM", "Name mismatch between PFMS and bank"),
    ("ACCL", "Account closed"),
)

DEFECTS = (
    "Income certificate not legible. Upload a clearer copy.",
    "Income certificate is for an old financial year. Upload the current one.",
    "Bonafide certificate missing institute seal.",
    "Fee receipt does not match the fee structure. Upload the correct receipt.",
    "Bank passbook name does not match the application.",
)


def _rng(person: Person, salt: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f"{person.id}:{salt}".encode()).hexdigest()[:12], 16))


def _person(reference_key: str) -> Person:
    person = population().by_uid_token(reference_key)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No person with that reference key")
    return person


def _payments(
    person: Person, rng: random.Random, amount: int, count: int, start: date
) -> list[dict[str, Any]]:
    payments = []
    for number in range(1, count + 1):
        when = start + timedelta(days=45 * (number - 1))
        entry: dict[str, Any] = {
            "instalment": number,
            "amount": amount,
            "initiated_on": when.isoformat(),
            "pfms_status": "Credited",
            "credited_on": (when + timedelta(days=rng.randint(3, 12))).isoformat(),
            "utr": f"PFMS{rng.randint(10**9, 10**10 - 1)}",
            "failure_code": None,
            "failure_reason": None,
        }
        if not person.bank_seeded and number == count:
            code, reason = PFMS_FAILURES[0]
            entry |= {
                "pfms_status": "Failed",
                "credited_on": None,
                "utr": None,
                "failure_code": code,
                "failure_reason": reason,
            }
        elif number == count and rng.random() < 0.08:
            code, reason = rng.choice(PFMS_FAILURES[1:])
            entry |= {
                "pfms_status": "Failed",
                "credited_on": None,
                "utr": None,
                "failure_code": code,
                "failure_reason": reason,
            }
        elif number == count and rng.random() < 0.15:
            entry |= {"pfms_status": "Pending at Bank", "credited_on": None, "utr": None}
        payments.append(entry)
    return payments


def nsp_applications(person: Person) -> list[dict[str, Any]]:
    if not person.has_scholarship_record or person.mota_award not in NSP_SCHEMES:
        return []
    rng = _rng(person, "nsp")
    stage_index = rng.choices(range(len(NSP_STAGES)), (8, 14, 10, 8, 6, 10, 44))[0]
    defective = stage_index <= 3 and rng.random() < 0.3
    stage = NSP_STAGES[stage_index]
    submitted = date.today() - timedelta(days=rng.randint(60, 160))
    history = []
    when = submitted
    for index in range(stage_index + 1):
        history.append({"status": NSP_STAGES[index], "on": when.isoformat()})
        when += timedelta(days=rng.randint(5, 25))
    last_change = date.fromisoformat(history[-1]["on"])
    if defective:
        level = ("Institute", "District", "State", "State")[stage_index]
        history.append(
            {
                "status": f"Marked Defective by {level}",
                "on": (last_change + timedelta(days=4)).isoformat(),
            }
        )
    amount = {"pre_matric": 3250, "post_matric": 18500, "top_class": 96000}[person.mota_award]
    payments = []
    if stage_index >= 5:
        payments = _payments(person, rng, amount // 2, 2 if stage_index == 6 else 1, last_change)
    return [
        {
            "application_id": f"NSP{person.state.code}{rng.randint(10**9, 10**10 - 1)}",
            "scheme_code": NSP_SCHEMES[person.mota_award],
            "academic_year": "2026-27",
            "applicant_name": person.name,
            "institute": person.institution.name if person.institution else None,
            "status": f"Defective at {history[-1]['status'].rsplit(' ', 1)[-1]}"
            if defective
            else stage,
            "defect_remarks": rng.choice(DEFECTS) if defective else None,
            "history": history,
            "sanctioned_amount": amount if stage_index >= 4 else None,
            "payments": payments,
        }
    ]


def sfmp_fellowships(person: Person) -> list[dict[str, Any]]:
    if not person.has_scholarship_record or person.mota_award != "nfst":
        return []
    rng = _rng(person, "sfmp")
    state = rng.choices(
        (
            "Provisionally Selected",
            "Joining Report Pending",
            "Active",
            "Continuation Certificate Due",
        ),
        (10, 15, 55, 20),
    )[0]
    joined = date.today() - timedelta(days=rng.randint(200, 700))
    months_paid = (
        0 if state in ("Provisionally Selected", "Joining Report Pending") else rng.randint(3, 20)
    )
    payments = []
    for month in range(months_paid):
        paid_on = joined + timedelta(days=30 * (month + 1))
        payments.append(
            {
                "instalment": month + 1,
                "amount": 37000,
                "initiated_on": paid_on.isoformat(),
                "pfms_status": "Credited",
                "credited_on": (paid_on + timedelta(days=4)).isoformat(),
                "utr": f"CNRB{rng.randint(10**9, 10**10 - 1)}",
                "failure_code": None,
                "failure_reason": None,
            }
        )
    if state == "Continuation Certificate Due" and payments:
        payments[-1] |= {
            "pfms_status": "On Hold",
            "credited_on": None,
            "utr": None,
            "failure_code": "CCDUE",
            "failure_reason": "Quarterly continuation certificate not uploaded",
        }
    return [
        {
            "fellow_id": f"NFST{rng.randint(10**7, 10**8 - 1)}",
            "award_year": "2024-25",
            "university": person.institution.name if person.institution else None,
            "fellowship_state": state,
            "joined_on": joined.isoformat() if months_paid else None,
            "monthly_amount": 37000,
            "next_continuation_due": "2026-10-10" if state != "Provisionally Selected" else None,
            "payments": payments,
        }
    ]


def nos_applications(person: Person) -> list[dict[str, Any]]:
    if not person.has_scholarship_record or person.mota_award != "nos":
        return []
    rng = _rng(person, "nos")
    state = rng.choice(
        ("Under Scrutiny", "Provisionally Selected", "Award Letter Issued", "Disbursal Started")
    )
    return [
        {
            "application_no": f"NOS{rng.randint(10**6, 10**7 - 1)}",
            "selection_year": "2026-27",
            "course": "Master's",
            "university_abroad": "University of Edinburgh",
            "state": state,
            "embassy": "High Commission of India, London" if state == "Disbursal Started" else None,
            "payments": _payments(person, rng, 900000, 1, date.today() - timedelta(days=20))
            if state == "Disbursal Started"
            else [],
        }
    ]


@router.get("/nsp/applications", tags=["NSP"])
async def nsp(reference_key: str = Query(...)) -> dict[str, Any]:
    return {"applications": nsp_applications(_person(reference_key))}


@router.get("/sfmp/fellows", tags=["SFMP"])
async def sfmp(reference_key: str = Query(...)) -> dict[str, Any]:
    return {"fellows": sfmp_fellowships(_person(reference_key))}


@router.get("/nos/applications", tags=["NOS Portal"])
async def nos(reference_key: str = Query(...)) -> dict[str, Any]:
    return {"applications": nos_applications(_person(reference_key))}
