"""Deciding what to chase: pure rules over a Student's applications and open Exceptions."""

from dataclasses import dataclass
from datetime import date

import pankh_rules
from app.applications.tracker import Application

# Which office acts on an application waiting at each step.
_OFFICE_LEVEL = {
    "institute": "institute",
    "district": "district",
    "state": "state",
    "sanctioning authority": "state",
    "university": "institute",
}


@dataclass(frozen=True)
class Proposal:
    audience: str  # student | office
    kind: str
    message: str
    dedupe_key: str
    level: str | None = None


@dataclass(frozen=True)
class OpenIssue:
    id: str
    kind: str
    message: str
    remedy: str | None


def plan(applications: list[Application], issues: list[OpenIssue], today: date) -> list[Proposal]:
    proposals: list[Proposal] = []
    for app in applications:
        scheme = pankh_rules.SCHEMES[app.scheme_id].short_name
        if app.deficiency and app.waiting_on in ("you", "university"):
            proposals.append(
                Proposal(
                    "student",
                    "deficiency",
                    f"{scheme}: {app.deficiency.reason} {app.deficiency.fix}",
                    f"deficiency:{app.source_system}:{app.external_id}:{app.status_text}",
                )
            )
        for instalment in app.instalments:
            problem = instalment.problem
            if problem is None:
                continue
            amount = f"₹{instalment.amount:,}"
            proposals.append(
                Proposal(
                    "student",
                    "payment_problem",
                    f"{scheme}: instalment {instalment.number} of {amount} did not reach you. "
                    f"{problem.reason} {problem.fix}",
                    ":".join(
                        (
                            "payment",
                            app.source_system,
                            app.external_id,
                            str(instalment.number),
                            instalment.status.value,
                        )
                    ),
                )
            )
        if app.is_stalled(today) and app.waiting_on in _OFFICE_LEVEL:
            days = app.days_waiting(today)
            proposals.append(
                Proposal(
                    "office",
                    "stalled_application",
                    f"{scheme} application {app.external_id} has waited {days} days for "
                    f"{app.waiting_on} verification, beyond the guideline timeline of about 30 "
                    "days. Please verify it or mark what the student must correct.",
                    f"stall:{app.source_system}:{app.external_id}:{app.status_text}",
                    level=_OFFICE_LEVEL[app.waiting_on],
                )
            )
    for issue in issues:
        if issue.kind == "stale_document" and issue.remedy:
            proposals.append(
                Proposal(
                    "student",
                    "stale_document",
                    f"{issue.message} {issue.remedy}",
                    f"issue:{issue.id}",
                )
            )
    return proposals
