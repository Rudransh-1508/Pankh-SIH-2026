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
from pankh_rules.institutes import TopClassInstitute, top_class_institutes
from pankh_rules.schemes import SCHEMES, Benefit, Rule, Scheme

__all__ = [
    "SCHEMES",
    "Benefit",
    "Citation",
    "FactError",
    "FactKind",
    "FactSpec",
    "Outcome",
    "Rule",
    "RuleResult",
    "Scheme",
    "SchemeResult",
    "Source",
    "Status",
    "TopClassInstitute",
    "UnsupportedAcademicYear",
    "evaluate",
    "fact_specs",
    "next_facts",
    "sources",
    "top_class_institutes",
    "validate_facts",
]
