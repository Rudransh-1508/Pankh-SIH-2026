"""One view of every Application, whichever system of record holds it.

NSP, SFMP and the NOS Portal each describe progress in their own words. Here each is mapped
onto the common Application Stages, with who the application is waiting on and since when,
so a stalled application can be spotted, and each payment is traced to credit or failure.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class Stage(StrEnum):
    SUBMITTED = "submitted"
    UNDER_VERIFICATION = "under_verification"
    SANCTIONED = "sanctioned"
    DISBURSING = "disbursing"
    CLOSED = "closed"
    REJECTED = "rejected"


class InstalmentStatus(StrEnum):
    CREDITED = "credited"
    PENDING = "pending"
    ON_HOLD = "on_hold"
    FAILED = "failed"


@dataclass(frozen=True)
class Problem:
    reason: str
    fix: str


@dataclass(frozen=True)
class Instalment:
    number: int
    amount: int
    status: InstalmentStatus
    initiated_on: date | None
    credited_on: date | None
    reference: str | None
    problem: Problem | None


@dataclass(frozen=True)
class TimelineEntry:
    label: str
    on: date


@dataclass(frozen=True)
class Application:
    source_system: str
    external_id: str
    scheme_id: str
    academic_year: str
    stage: Stage
    status_text: str
    waiting_on: str | None
    since: date | None
    deficiency: Problem | None
    sanctioned_amount: int | None
    timeline: list[TimelineEntry] = field(default_factory=list)
    instalments: list[Instalment] = field(default_factory=list)

    def days_waiting(self, today: date) -> int | None:
        return (today - self.since).days if self.since else None

    def is_stalled(self, today: date) -> bool:
        """Waiting longer than the guideline timelines allow at this step."""
        days = self.days_waiting(today)
        limit = STALL_AFTER_DAYS.get(self.waiting_on or "")
        return days is not None and limit is not None and days > limit and self.deficiency is None

    @property
    def active(self) -> bool:
        return self.stage not in (Stage.CLOSED, Stage.REJECTED)

    @property
    def received(self) -> int:
        return sum(i.amount for i in self.instalments if i.status is InstalmentStatus.CREDITED)


# Guideline timelines give each verification level about a month (Pre-Matric guidelines, para 6).
STALL_AFTER_DAYS = {"institute": 30, "district": 30, "state": 30, "sanctioning authority": 45}

PAYMENT_PROBLEMS = {
    "ACNS": Problem(
        "Your bank account is not linked with your Aadhaar for direct benefit transfer.",
        "Visit your bank with your Aadhaar card and ask them to link (seed) it for DBT. "
        "The payment is sent again once it is linked.",
    ),
    "ACIN": Problem(
        "Your bank account is inactive.",
        "Visit your bank to make the account active again, usually by updating your KYC.",
    ),
    "NMMM": Problem(
        "Your name in the bank's records does not match your application.",
        "Ask your bank to correct your name to match your Aadhaar, or ask your institute to "
        "correct the application.",
    ),
    "ACCL": Problem(
        "This bank account is closed.",
        "Give your institute the details of a working account linked with your Aadhaar.",
    ),
    "CCDUE": Problem(
        "Your fellowship is on hold because this quarter's continuation certificate has not "
        "been uploaded.",
        "Ask your university to upload the continuation certificate on the fellowship portal.",
    ),
}

_NSP_SCHEMES = {
    "PRE-MATRIC-ST": "pre_matric",
    "POST-MATRIC-ST": "post_matric",
    "TOPCLASS-ST": "top_class",
}

_NSP_STAGES = {
    "Submitted": (Stage.UNDER_VERIFICATION, "institute"),
    "Verified by Institute": (Stage.UNDER_VERIFICATION, "district"),
    "Verified by District": (Stage.UNDER_VERIFICATION, "state"),
    "Verified by State": (Stage.UNDER_VERIFICATION, "sanctioning authority"),
    "Sanctioned": (Stage.SANCTIONED, None),
    "Payment Initiated": (Stage.DISBURSING, None),
    "Paid": (Stage.CLOSED, None),
}

_DEFECT_LEVELS = {"Institute": "institute", "District": "district", "State": "state"}


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _instalments(payments: list[dict[str, Any]]) -> list[Instalment]:
    statuses = {
        "Credited": InstalmentStatus.CREDITED,
        "Failed": InstalmentStatus.FAILED,
        "On Hold": InstalmentStatus.ON_HOLD,
    }
    result = []
    for payment in payments:
        status = statuses.get(payment["pfms_status"], InstalmentStatus.PENDING)
        code = payment.get("failure_code")
        problem = None
        if code:
            problem = PAYMENT_PROBLEMS.get(
                code,
                Problem(
                    payment.get("failure_reason") or "The payment did not go through.",
                    "Ask your institute's scholarship nodal officer to check it with PFMS.",
                ),
            )
        result.append(
            Instalment(
                number=payment["instalment"],
                amount=payment["amount"],
                status=status,
                initiated_on=_date(payment.get("initiated_on")),
                credited_on=_date(payment.get("credited_on")),
                reference=payment.get("utr"),
                problem=problem,
            )
        )
    return result


def from_nsp(record: dict[str, Any]) -> Application:
    history = [TimelineEntry(h["status"], date.fromisoformat(h["on"])) for h in record["history"]]
    status_text = record["status"]
    deficiency = None
    if status_text.startswith("Defective"):
        level = _DEFECT_LEVELS.get(status_text.rsplit(" ", 1)[-1], "institute")
        stage, waiting_on = Stage.UNDER_VERIFICATION, "you"
        deficiency = Problem(
            f"Your {level} marked the application defective: {record['defect_remarks']}",
            "Correct it on the National Scholarship Portal and resubmit before the last date. "
            f"It then goes back to your {level} for verification.",
        )
    else:
        stage, waiting_on = _NSP_STAGES.get(status_text, (Stage.SUBMITTED, None))
    return Application(
        source_system="NSP",
        external_id=record["application_id"],
        scheme_id=_NSP_SCHEMES[record["scheme_code"]],
        academic_year=record["academic_year"],
        stage=stage,
        status_text=status_text,
        waiting_on=waiting_on,
        since=history[-1].on if history else None,
        deficiency=deficiency,
        sanctioned_amount=record.get("sanctioned_amount"),
        timeline=history,
        instalments=_instalments(record["payments"]),
    )


def from_sfmp(record: dict[str, Any]) -> Application:
    state = record["fellowship_state"]
    stage, waiting_on, deficiency = {
        "Provisionally Selected": (
            Stage.SANCTIONED,
            "you",
            Problem(
                "You are provisionally selected for the fellowship.",
                "Join your university and have it submit your joining report within one month.",
            ),
        ),
        "Joining Report Pending": (
            Stage.SANCTIONED,
            "university",
            Problem(
                "Your joining report has not reached the Ministry yet.",
                "Ask your university's nodal officer to submit your joining report on the "
                "fellowship portal.",
            ),
        ),
        "Active": (Stage.DISBURSING, None, None),
        "Continuation Certificate Due": (Stage.DISBURSING, "university", PAYMENT_PROBLEMS["CCDUE"]),
    }.get(state, (Stage.SANCTIONED, None, None))
    joined = _date(record.get("joined_on"))
    timeline = [TimelineEntry("Joined", joined)] if joined else []
    return Application(
        source_system="SFMP",
        external_id=record["fellow_id"],
        scheme_id="nfst",
        academic_year=record["award_year"],
        stage=stage,
        status_text=state,
        waiting_on=waiting_on,
        since=joined,
        deficiency=deficiency,
        sanctioned_amount=record.get("monthly_amount"),
        timeline=timeline,
        instalments=_instalments(record["payments"]),
    )


def from_nos(record: dict[str, Any]) -> Application:
    state = record["state"]
    stage, waiting_on = {
        "Under Scrutiny": (Stage.UNDER_VERIFICATION, "ministry"),
        "Provisionally Selected": (Stage.SANCTIONED, None),
        "Award Letter Issued": (Stage.SANCTIONED, None),
        "Disbursal Started": (Stage.DISBURSING, None),
    }.get(state, (Stage.SUBMITTED, None))
    return Application(
        source_system="NOS Portal",
        external_id=record["application_no"],
        scheme_id="nos",
        academic_year=record["selection_year"],
        stage=stage,
        status_text=state,
        waiting_on=waiting_on,
        since=None,
        deficiency=None,
        sanctioned_amount=None,
        instalments=_instalments(record["payments"]),
    )


def exclusivity_warning(applications: list[Application]) -> str | None:
    """A Student may hold only one Ministry of Tribal Affairs scholarship at a time."""
    active = sorted({a.scheme_id for a in applications if a.active})
    if len(active) > 1:
        return (
            "You have active applications for more than one Ministry of Tribal Affairs "
            "scholarship. Only one can be held at a time; tell your institute which to keep."
        )
    return None
