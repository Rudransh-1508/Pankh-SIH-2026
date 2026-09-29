"""The Scheme Path: which scholarship to hold at each stage of a Student's education.

A Student can hold only one scholarship at a time, so the question is not only what they can
get now but what to aim for over the years. The planner projects the Student through the
stages ahead, judges every Scheme at each stage with the same Rules, recommends one, and points
out opportunities: an achievable condition (admission to a Top Class institute, qualifying NET,
an offer from a university abroad) that would unlock a better Scheme at that stage.

Amounts come from the Schemes' cited benefit clauses. Where an amount depends on the course,
as Post-Matric fees do, the planner says so rather than invent a figure.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pankh_rules.citations import Citation, cite
from pankh_rules.engine import Status, evaluate, validate_facts

# Stages of education in order, with how many academic years each usually takes.
STAGES: tuple[tuple[str, int], ...] = (
    ("class_9", 1),
    ("class_10", 1),
    ("class_11", 1),
    ("class_12", 1),
    ("undergraduate", 3),
    ("postgraduate", 2),
    ("phd", 4),
)


@dataclass(frozen=True)
class Value:
    """What a Scheme pays in a year, as far as the Guidelines fix it."""

    yearly_inr: int | None
    text: str
    citation: Citation
    rank: int
    """For choosing between Schemes when amounts are not comparable: higher is better."""


def _value(scheme_id: str, year_in_stage: int) -> Value:
    match scheme_id:
        case "pre_matric":
            return Value(
                3_000,
                "₹2,250 scholarship and ₹750 books grant a year (day scholars)",
                cite("pre-matric-guidelines-2022", 4, "para 3.4"),
                10,
            )
        case "post_matric":
            return Value(
                None,
                "Monthly maintenance allowance and all compulsory fees (amount depends on the course)",
                cite("post-matric-regulations", 9, "section V"),
                40,
            )
        case "top_class":
            return Value(
                41_000,
                "Full fees, plus ₹3,000 a month stipend and ₹5,000 for books a year",
                cite("nfs-guidelines-2022", 19, "Part B para 2.5"),
                60,
            )
        case "nfst":
            monthly = 37_000 if year_in_stage < 2 else 42_000
            return Value(
                monthly * 12,
                f"₹{monthly:,} a month fellowship, plus contingency grant",
                cite("nfst-rate-revision-2023", 1, "revised rates from 01.01.2023"),
                70,
            )
        case "nos":
            return Value(
                None,
                "Tuition, US$15,400 a year to live on, and air fare, for study abroad",
                cite("nos-guidelines-2022", 5, "para 3.2"),
                80,
            )
        case "csss":
            yearly = 12_000 if year_in_stage < 3 else 20_000
            return Value(
                yearly, f"₹{yearly:,} a year", cite("csss-guidelines-2022", 3, "para 7"), 20
            )
        case "pragati":
            return Value(
                50_000, "₹50,000 a year", cite("pragati-degree-guidelines-2021", 2, "para 4.0"), 30
            )
        case "nmmss":
            return Value(12_000, "₹12,000 a year", cite("nmmss-guidelines-2022", 4, "para 1.3"), 15)
    raise KeyError(scheme_id)


# Conditions a Student can work towards, and the Facts that describe achieving them.
OPPORTUNITIES: dict[str, tuple[dict[str, Any], str]] = {
    "top_class": (
        {"admitted_to_top_class_institute": True, "admitted_via_management_quota": False},
        "Get admission (not through a management quota) to one of the 265 Top Class institutes.",
    ),
    "nfst": (
        {
            "net_jrf_qualified": True,
            "masters_marks_percent": 55.0,
            "institution_eligible_for_fellowship": True,
        },
        "Score at least 55% in your Master's, qualify UGC NET or CSIR NET, and join a UGC-recognised or government-funded university.",
    ),
    "nos": (
        {
            "has_overseas_admission_offer": True,
            "studies_abroad": True,
            "overseas_admission_in_qs_top_1000": True,
        },
        "Get an offer of admission from a university in the QS World University Rankings top 1,000.",
    ),
    "csss": (
        {"class_12_top_20_percent": True, "studies_by_distance": False},
        "Finish in the top 20% of Class XII passes in your stream and board.",
    ),
    "pragati": (
        {"aicte_technical_first_year": True, "joined_within_two_years_of_class_12": True},
        "Join a technical degree at an AICTE-approved college within two years of Class XII.",
    ),
}


@dataclass(frozen=True)
class Option:
    scheme_id: str
    scheme: str
    value: Value
    condition: str | None = None
    """What the Student must achieve first, or None if they already qualify on what we know."""


@dataclass(frozen=True)
class Stage:
    level: str
    first_year: int
    years: int
    recommended: Option | None
    needs_answers: bool
    """True when the recommendation may change once the Student answers more questions."""
    opportunities: list[Option] = field(default_factory=list)

    @property
    def label(self) -> str:
        last = self.first_year + self.years - 1
        return f"{self.first_year}-{(self.first_year + 1) % 100:02d}" + (
            "" if self.years == 1 else f" to {last}-{(last + 1) % 100:02d}"
        )


def _stages_from(level: str) -> list[tuple[str, int]]:
    names = [name for name, _ in STAGES]
    if level not in names:
        return []
    return list(STAGES[names.index(level) :])


def _projected(facts: Mapping[str, Any], level: str) -> dict[str, Any]:
    """The Student's Facts as they might be at a later stage.

    Answers tied to the current course (institution, admission route, exam results) no longer
    hold; answers about the Student and their family carry forward.
    """
    carried = {
        name: value
        for name, value in facts.items()
        if name
        in {
            "is_scheduled_tribe",
            "date_of_birth",
            "family_income",
            "gender",
            "is_orphan_supported_by_guardian",
            "has_aadhaar_seeded_bank_account",
            "repeating_stage_in_other_subject",
            "sibling_received_nos",
            "previously_received_nos",
            "holds_other_scholarship",
        }
    }
    return carried | {
        "education_level": level,
        "studies_abroad": False,
        "institution_recognised": True,
        "current_mota_award": "none",
        "admitted_to_top_class_institute": False,
        "school_government_aided_or_local_body": True,
    }


def plan_path(facts: Mapping[str, Any], academic_year: int | None = None) -> list[Stage]:
    known = validate_facts(facts)
    level = known.get("education_level")
    if level is None:
        return []
    year = academic_year or (
        date.today().year if date.today().month >= 4 else date.today().year - 1
    )
    stages: list[Stage] = []
    start = year
    for index, (stage_level, years) in enumerate(_stages_from(level)):
        base = dict(known) if index == 0 else _projected(known, stage_level)
        results = {r.scheme.id: r for r in evaluate(base, start)}
        eligible = [
            Option(sid, r.scheme.short_name, _value(sid, 0))
            for sid, r in results.items()
            if r.status is Status.ELIGIBLE
        ]
        best_rank = max((o.value.rank for o in eligible), default=0)
        # Only undecided Schemes that could beat the recommendation are worth more questions.
        possible = [
            sid
            for sid, r in results.items()
            if r.status is Status.NEEDS_INFORMATION and _value(sid, 0).rank > best_rank
        ]
        opportunities = []
        for sid, (extra, condition) in OPPORTUNITIES.items():
            if sid in {o.scheme_id for o in eligible} or _value(sid, 0).rank <= best_rank:
                continue
            (tried,) = evaluate(base | extra, start, [sid])
            if tried.status is not Status.NOT_ELIGIBLE:
                opportunities.append(
                    Option(sid, tried.scheme.short_name, _value(sid, 0), condition)
                )
        recommended = max(eligible, key=lambda o: o.value.rank, default=None)
        stages.append(
            Stage(
                level=stage_level,
                first_year=start,
                years=years,
                recommended=recommended,
                needs_answers=bool(possible),
                opportunities=sorted(opportunities, key=lambda o: -o.value.rank),
            )
        )
        start += years
    return stages
