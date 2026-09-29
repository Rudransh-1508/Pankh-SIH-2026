"""The grievance agent: when to take a stuck case to CPGRAMS, and what to write.

Only problems past their deadline that the Student cannot fix themselves qualify. A payment
that failed because of the Student's bank account is theirs to fix, and filing a grievance
would only delay them; an office that has not acted in time, even after a reminder, is not.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pankh_rules
from app.applications.tracker import STALL_AFTER_DAYS, Application, InstalmentStatus

# A payment sent to the bank should be credited within days; a month means it is stuck.
PAYMENT_STUCK_AFTER_DAYS = 30
# How long an office has after a reminder before a grievance is the next step.
AFTER_REMINDER = timedelta(days=14)

CATEGORY = "Scholarship"


@dataclass(frozen=True)
class Draft:
    key: str
    kind: str  # payment_stuck | application_stalled
    scheme: str
    reason: str
    """Why a grievance is the right step now, for the Student."""
    subject: str
    description: str


def _scheme(application: Application) -> str:
    return pankh_rules.SCHEMES[application.scheme_id].name


def drafts(
    applications: list[Application],
    reminded: dict[str, datetime],
    filed: set[str],
    today: date,
) -> list[Draft]:
    """Grievances the Student could file now.

    `reminded` maps an application's stall key to when its office was reminded; `filed` holds
    the keys already taken to CPGRAMS.
    """
    found: list[Draft] = []
    for app in applications:
        scheme = _scheme(app)
        header = (
            f"Application {app.external_id} on the {app.source_system} for the {scheme}, "
            f"academic year {app.academic_year}."
        )
        for instalment in app.instalments:
            if instalment.status is not InstalmentStatus.PENDING or instalment.initiated_on is None:
                continue
            days = (today - instalment.initiated_on).days
            key = f"payment:{app.source_system}:{app.external_id}:{instalment.number}"
            if days <= PAYMENT_STUCK_AFTER_DAYS or key in filed:
                continue
            found.append(
                Draft(
                    key,
                    "payment_stuck",
                    scheme,
                    f"Instalment {instalment.number} was sent to your bank {days} days ago and "
                    "has still not been credited.",
                    f"{scheme}: instalment {instalment.number} not credited after {days} days",
                    f"{header} Instalment {instalment.number} of Rs. {instalment.amount:,} was "
                    f"initiated through PFMS on {instalment.initiated_on:%d %B %Y} and has shown "
                    f"as pending at the bank for {days} days, with no credit or failure reason. "
                    "I request that the payment be traced with PFMS and the bank, and credited "
                    "to my Aadhaar-linked account, or that I be told what I must do.",
                )
            )
        limit = STALL_AFTER_DAYS.get(app.waiting_on or "")
        days = app.days_waiting(today)
        stall_key = f"stall:{app.source_system}:{app.external_id}:{app.status_text}"
        if not app.is_stalled(today) or limit is None or days is None or stall_key in filed:
            continue
        reminder = reminded.get(stall_key)
        waited_after_reminder = reminder is not None and today - reminder.date() >= AFTER_REMINDER
        if not waited_after_reminder and days < 2 * limit:
            continue
        office = app.waiting_on
        found.append(
            Draft(
                stall_key,
                "application_stalled",
                scheme,
                f"Your application has waited {days} days for {office} verification, against a "
                f"guideline of about {limit} days"
                + (", even after a reminder to the office." if reminder else "."),
                f"{scheme}: application pending {office} verification for {days} days",
                f"{header} The application has been pending {office} verification since "
                f"{app.since:%d %B %Y} ({days} days), while the scheme guidelines allow about "
                f"{limit} days for each level"
                + (f"; the office was reminded on {reminder:%d %B %Y}" if reminder else "")
                + ". I request that it be verified, or that I be told what I must correct.",
            )
        )
    return found
