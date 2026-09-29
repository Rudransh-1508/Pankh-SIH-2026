"""MoTA scholarship Scheme Rules as code, with citations to the official Guidelines."""

from pankh_rules.citations import Citation, Source, sources
from pankh_rules.engine import (
    FactError,
    FactKind,
    FactSpec,
    Outcome,
    RuleResult,
    SchemeResult,
    Status,
    UnsupportedAcademicYear,
    evaluate,
    fact_specs,
    next_facts,
    validate_facts,
)
from pankh_rules.institutes import TopClassInstitute, search_top_class, top_class_institutes
from pankh_rules.planner import Option, Stage, plan_path
from pankh_rules.schemes import MOTA_SCHEME_IDS, SCHEMES, Benefit, Rule, Scheme

__all__ = [
    "MOTA_SCHEME_IDS",
    "SCHEMES",
    "Benefit",
    "Citation",
    "FactError",
    "FactKind",
    "FactSpec",
    "Option",
    "Outcome",
    "Rule",
    "RuleResult",
    "Scheme",
    "SchemeResult",
    "Source",
    "Stage",
    "Status",
    "TopClassInstitute",
    "UnsupportedAcademicYear",
    "evaluate",
    "fact_specs",
    "next_facts",
    "plan_path",
    "search_top_class",
    "sources",
    "top_class_institutes",
    "validate_facts",
]
