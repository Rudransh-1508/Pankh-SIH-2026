"""The renewal agent: next year's application for a Scheme the Student holds now.

It carries forward everything that stays true, asks only what changes from year to year, and
judges next year with the same Rules. It never applies on the Student's behalf; it tells them
what the portal will ask and what they must get ready first.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import pankh_rules
from app.academic_year import label
from app.applications.tracker import Application, Stage
from app.facts.service import FactStatus

# Where a Student usually goes next, when the next class is certain.
NEXT_LEVEL = {
    "class_9": "class_10",
    "class_10": "class_11",
    "class_11": "class_12",
    "class_12": "undergraduate",
}

HELD_STAGES = (Stage.SANCTIONED, Stage.DISBURSING, Stage.CLOSED)

# Facts that stay true from one year to the next, so a renewal never asks them again.
STABLE_FACTS = ("is_scheduled_tribe", "date_of_birth", "gender", "is_orphan_supported_by_guardian")


@dataclass(frozen=True)
class Check:
    id: str
    text: str
    done: bool
    fact: str | None = None
    """The Fact to update when this is not done, if answering a question settles it."""


@dataclass(frozen=True)
class Plan:
    scheme_id: str
    scheme: str
    held_year: str
    next_year: str
    next_level: str | None
    continuing: bool
    """False when the next stage needs a different Scheme, so it is a fresh application."""
    instead: str | None
    status: str
    unmet: list[str]
    checks: list[Check] = field(default_factory=list)
    apply_on: str = ""
    apply_url: str = ""
    window: str | None = None
    carried: list[str] = field(default_factory=list)


def held_schemes(applications: list[Application], facts: dict[str, Any]) -> dict[str, int]:
    """Schemes the Student holds, with the academic year (start) they hold them for."""
    held: dict[str, int] = {}
    for application in applications:
        if application.stage in HELD_STAGES:
            start = int(application.academic_year[:4])
            held[application.scheme_id] = max(start, held.get(application.scheme_id, start))
    return held


def _proof_lasts(status: FactStatus | None, until: date) -> bool:
    return bool(
        status and status.verified and status.expires_at and status.expires_at.date() >= until
    )


def plan(
    scheme_id: str,
    held_year: int,
    statuses: dict[str, FactStatus],
    today: date | None = None,
) -> Plan:
    scheme = pankh_rules.SCHEMES[scheme_id]
    facts = {name: s.value for name, s in statuses.items()}
    next_year = held_year + 1
    level = facts.get("education_level")
    next_level = NEXT_LEVEL.get(level, level) if isinstance(level, str) else None
    projected = facts | {
        "current_mota_award": scheme_id,
        "studies_abroad": facts.get("studies_abroad", False),
    }
    if next_level:
        projected["education_level"] = next_level
    (result,) = pankh_rules.evaluate(projected, next_year, [scheme_id])
    failed = [r for r in result.rules if r.outcome is pankh_rules.Outcome.FAIL]
    # The Scheme ends at this stage (Pre-Matric after Class X, say): next year is a new Scheme.
    continuing = not any("education_level" in r.rule.requires for r in failed)
    instead = None
    if not continuing:
        # The best Scheme still possible next year: confirmed ones first, then the Ministry's.
        possible = [
            r
            for r in pankh_rules.evaluate(projected | {"current_mota_award": "none"}, next_year)
            if r.status is not pankh_rules.Status.NOT_ELIGIBLE
        ]
        possible.sort(
            key=lambda r: (r.status is not pankh_rules.Status.ELIGIBLE, r.scheme.kind != "mota")
        )
        instead = possible[0].scheme.short_name if possible else None

    # Income must be for the financial year before the session being applied for.
    financial_year = f"{next_year - 1}-{next_year % 100:02d}"
    session_start = date(next_year, 7, 1)
    checks = [
        Check(
            "promoted",
            "You pass this year's exams or are promoted to the next class or year. "
            "Renewal depends on it.",
            done=False,
        ),
        Check(
            "income",
            f"An income certificate for {financial_year}. Get it from your tehsil or e-District "
            "after 1 April, then add it here so it can be checked.",
            done=_proof_lasts(statuses.get("family_income"), session_start),
            fact="family_income",
        ),
        Check(
            "bank",
            "Your bank account is still linked to Aadhaar. Money goes only to a linked account.",
            done=_proof_lasts(statuses.get("has_aadhaar_seeded_bank_account"), session_start),
            fact="has_aadhaar_seeded_bank_account",
        ),
    ]
    if next_level != level:
        checks.append(
            Check(
                "institution",
                "Your admission for next year, and your school or college's code for the "
                "application.",
                done=False,
                fact="institution_recognised",
            )
        )
    specs = pankh_rules.fact_specs()
    stable = [
        specs[name].label
        for name in (
            "is_scheduled_tribe",
            "date_of_birth",
            "gender",
            "is_orphan_supported_by_guardian",
        )
        if name in facts and name in specs
    ]
    return Plan(
        scheme_id=scheme_id,
        scheme=scheme.short_name,
        held_year=label(held_year),
        next_year=label(next_year),
        next_level=next_level,
        continuing=continuing,
        instead=instead,
        status=result.status.value,
        unmet=[r.reason for r in failed if r.reason],
        checks=checks,
        apply_on=scheme.system_of_record,
        apply_url=scheme.apply_url,
        window=scheme.application_window,
        carried=stable,
    )


def plans(
    applications: list[Application], statuses: dict[str, FactStatus], today: date | None = None
) -> list[Plan]:
    facts = {name: s.value for name, s in statuses.items()}
    held = held_schemes(applications, facts)
    if not held and facts.get("current_mota_award") not in (None, "none"):
        today = today or datetime.now(UTC).date()
        held[facts["current_mota_award"]] = today.year if today.month >= 4 else today.year - 1
    return [plan(scheme_id, year, statuses, today) for scheme_id, year in sorted(held.items())]
