"""Finding Unreached Students: enrolled ST students with no scholarship registration.

The UDISE+ roster of ST students is linked against NSP registrations. Students with no
Record Link, and no possible one, are unreached. For each, the rules engine says which
Schemes they could be eligible for, so outreach can say what to apply for.
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import pankh_rules
from app.academic_year import current_academic_year
from app.coverage.linkage import PersonRecord, RecordLink, link
from app.sources.registers import RegistersClient
from app.sources.scholarship_systems import ScholarshipSystemsClient

OFFICIAL_FIGURES = Path(__file__).resolve().parent / "data" / "mota_beneficiaries.csv"
OFFICIAL_SOURCE = (
    "Ministry of Tribal Affairs, Annexure I: Pre-Matric and Post-Matric Scholarship fund "
    "released, utilised and beneficiaries, FY 2013-14 to 2025-26 (tribal.nic.in)"
)


@dataclass(frozen=True)
class CoverageResult:
    summary: dict[str, Any]
    unreached: list[dict[str, Any]]


async def _all(fetch, **filters) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    while True:
        page = await fetch(offset=len(items), **filters)
        items += page["items"]
        if len(items) >= page["total"] or not page["items"]:
            return items


def _likely_schemes(class_level: str) -> list[dict[str, Any]]:
    facts = {
        "is_scheduled_tribe": True,
        "education_level": f"class_{class_level}",
        "studies_abroad": False,
    }
    results = pankh_rules.evaluate(facts, current_academic_year())
    return [
        {
            "scheme_id": r.scheme.id,
            "scheme": r.scheme.short_name,
            "to_confirm": list(r.missing_facts),
        }
        for r in results
        if r.status is not pankh_rules.Status.NOT_ELIGIBLE
    ]


@cache
def official_figures() -> list[dict[str, Any]]:
    with OFFICIAL_FIGURES.open(newline="") as handle:
        return [
            row
            | {"beneficiaries": int(row["beneficiaries"]), "estimated": row["estimated"] == "True"}
            for row in csv.DictReader(handle)
        ]


def latest_official_beneficiaries() -> dict[str, dict[str, Any]]:
    """For each state, Pre- plus Post-Matric beneficiaries in the latest published year."""
    rows = official_figures()
    latest = max(row["financial_year"] for row in rows)
    by_state: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"financial_year": latest, "total": 0}
    )
    for row in rows:
        if row["financial_year"] == latest:
            by_state[row["state"]][row["scheme"]] = row["beneficiaries"]
            by_state[row["state"]]["total"] += row["beneficiaries"]
    return dict(by_state)


async def compute_coverage(
    registers: RegistersClient, systems: ScholarshipSystemsClient
) -> CoverageResult:
    roster = await _all(registers.udise_students, social_category="ST", limit=1000)
    registrations = await _all(systems.nsp_registrations)
    enrolled = [
        PersonRecord(
            r["student_ref"], r["name"], r["date_of_birth"], r["gender"], r["district"], r["state"]
        )
        for r in roster
    ]
    registered = [
        PersonRecord(
            r["application_id"],
            r["applicant_name"],
            r["date_of_birth"],
            r["gender"],
            r["district"],
            r["state"],
        )
        for r in registrations
    ]
    links: dict[str, RecordLink] = {found.left_id: found for found in link(enrolled, registered)}

    districts: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"enrolled": 0, "reached": 0, "possible": 0, "unreached": 0}
    )
    unreached = []
    for record in roster:
        counts = districts[(record["state"], record["district"])]
        counts["enrolled"] += 1
        found = links.get(record["student_ref"])
        if found and found.is_link:
            counts["reached"] += 1
        elif found:
            counts["possible"] += 1
        else:
            counts["unreached"] += 1
            unreached.append(
                {
                    "student_ref": record["student_ref"],
                    "name": record["name"],
                    "class": record["class"],
                    "gender": record["gender"],
                    "district": record["district"],
                    "state": record["state"],
                    "udise_code": record["udise_code"],
                    "likely_schemes": _likely_schemes(record["class"]),
                }
            )

    official = latest_official_beneficiaries()
    states: dict[str, dict[str, Any]] = {}
    for (state, district), counts in sorted(districts.items()):
        entry = states.setdefault(
            state,
            {
                "state": state,
                "enrolled": 0,
                "reached": 0,
                "possible": 0,
                "unreached": 0,
                "districts": [],
                "official": official.get(state),
            },
        )
        for key in ("enrolled", "reached", "possible", "unreached"):
            entry[key] += counts[key]
        entry["districts"].append({"district": district, **counts, "coverage": _share(counts)})
    for entry in states.values():
        entry["coverage"] = _share(entry)
    totals = {
        key: sum(s[key] for s in states.values())
        for key in ("enrolled", "reached", "possible", "unreached")
    }
    summary = {
        "totals": totals | {"coverage": _share(totals)},
        "states": list(states.values()),
        "registrations": len(registered),
        "method": "Probabilistic record linkage (Splink) on Indic-aware name keys, date of "
        "birth and gender within districts. Possible links await confirmation.",
        "official_source": OFFICIAL_SOURCE,
    }
    return CoverageResult(summary, unreached)


def _share(counts: dict[str, int]) -> float:
    return round(counts["reached"] / counts["enrolled"], 3) if counts["enrolled"] else 0.0
