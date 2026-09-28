"""Judge a Student's Facts against Scheme Rules and explain every outcome.

A Rule whose required Facts are not all known is reported as `unknown`, never guessed: the
Student is told exactly which Facts are missing. Every judgment names the academic year whose
Rule Version it used.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from functools import cache
from typing import Any

from openfisca_core.indexed_enums import Enum as OpenFiscaEnum
from openfisca_core.simulation_builder import SimulationBuilder

from pankh_rules.questions import CHOICE_LABELS, GATING_FACTS, HELP, QUESTIONS
from pankh_rules.schemes import SCHEMES, Rule, Scheme
from pankh_rules.system import concrete_variables, pankh_system
from pankh_rules.variables import facts as fact_variables

FIRST_SUPPORTED_ACADEMIC_YEAR = 2021


class FactKind(StrEnum):
    BOOLEAN = "boolean"
    NUMBER = "number"
    DATE = "date"
    CHOICE = "choice"


@dataclass(frozen=True)
class Choice:
    key: str
    label: str
    labels: Mapping[str, str]
    """The label in each supported language, keyed by language code."""


@dataclass(frozen=True)
class FactSpec:
    name: str
    label: str
    description: str | None
    kind: FactKind
    question: Mapping[str, str]
    """How the Fact is asked of a Student, keyed by language code."""
    help: Mapping[str, str] | None = None
    choices: tuple[Choice, ...] = ()


class Outcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WAIVED = "waived"
    UNKNOWN = "unknown"


class Status(StrEnum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    NEEDS_INFORMATION = "needs_information"


@dataclass(frozen=True)
class RuleResult:
    rule: Rule
    outcome: Outcome
    title: str
    reason: str | None
    remedy: str | None
    missing_facts: tuple[str, ...]


@dataclass(frozen=True)
class SchemeResult:
    scheme: Scheme
    academic_year: int
    status: Status
    rules: tuple[RuleResult, ...]

    @property
    def missing_facts(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for result in self.rules:
            seen.update(dict.fromkeys(result.missing_facts))
        return tuple(seen)


class FactError(ValueError):
    """A Fact has an unknown name or a value of the wrong kind."""


class UnsupportedAcademicYear(ValueError):
    pass


@cache
def fact_specs() -> dict[str, FactSpec]:
    """Every Fact a Rule can use, with labels suitable for showing to Students."""
    specs = {}
    system = pankh_system()
    for cls in concrete_variables(fact_variables):
        variable = system.variables[cls.__name__]
        choices: tuple[Choice, ...] = ()
        if variable.value_type is bool:
            kind = FactKind.BOOLEAN
        elif variable.value_type in (int, float):
            kind = FactKind.NUMBER
        elif variable.value_type is date:
            kind = FactKind.DATE
        else:
            kind = FactKind.CHOICE
            labels = CHOICE_LABELS[variable.name]
            choices = tuple(
                Choice(item.name, item.value, labels[item.name])
                for item in variable.possible_values
                if item.name != "unknown"
            )
        specs[variable.name] = FactSpec(
            name=variable.name,
            label=variable.label,
            description=variable.documentation,
            kind=kind,
            question=QUESTIONS[variable.name],
            help=HELP.get(variable.name),
            choices=choices,
        )
    return specs


def validate_facts(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Check Fact names and kinds. `None` means not known and is dropped."""
    specs = fact_specs()
    clean: dict[str, Any] = {}
    for name, value in raw.items():
        if value is None:
            continue
        spec = specs.get(name)
        if spec is None:
            raise FactError(f"Unknown fact: {name}")
        clean[name] = _coerce(spec, value)
    return clean


def evaluate(
    facts: Mapping[str, Any],
    academic_year: int,
    scheme_ids: Iterable[str] | None = None,
) -> list[SchemeResult]:
    if academic_year < FIRST_SUPPORTED_ACADEMIC_YEAR:
        raise UnsupportedAcademicYear(
            f"Rules are available from the {FIRST_SUPPORTED_ACADEMIC_YEAR}-"
            f"{(FIRST_SUPPORTED_ACADEMIC_YEAR + 1) % 100:02d} academic year"
        )
    known = validate_facts(facts)
    schemes = [SCHEMES[scheme_id] for scheme_id in scheme_ids] if scheme_ids else SCHEMES.values()
    judge = _Judge(known, academic_year)
    return [judge.scheme(scheme) for scheme in schemes]


def next_facts(results: Iterable[SchemeResult]) -> list[str]:
    """Facts worth asking for next, most useful first.

    Facts that can rule out whole Schemes on their own come first, then those that would settle
    the most undecided Schemes. Schemes already ruled out are ignored, so a Student is never
    asked something that cannot change any outcome.
    """
    counts: dict[str, int] = {}
    for result in results:
        if result.status is Status.NEEDS_INFORMATION:
            for name in result.missing_facts:
                counts[name] = counts.get(name, 0) + 1
    declared = list(fact_specs())

    def priority(name: str) -> tuple[int, int, int]:
        gating = GATING_FACTS.index(name) if name in GATING_FACTS else len(GATING_FACTS)
        return gating, -counts[name], declared.index(name)

    return sorted(counts, key=priority)


class _Judge:
    def __init__(self, facts: dict[str, Any], academic_year: int) -> None:
        self.facts = facts
        self.period = f"{academic_year}-07"
        self.academic_year = academic_year
        system = pankh_system()
        self.parameters = system.parameters(f"{academic_year}-07-01")
        inputs = {name: {self.period: _to_openfisca(value)} for name, value in facts.items()}
        self.simulation = SimulationBuilder().build_from_entities(
            system, {"students": {"student": inputs}}
        )
        self.context = self._display_facts()

    def scheme(self, scheme: Scheme) -> SchemeResult:
        results = tuple(self.rule(rule) for rule in scheme.rules)
        outcomes = {result.outcome for result in results}
        if Outcome.FAIL in outcomes:
            status = Status.NOT_ELIGIBLE
        elif Outcome.UNKNOWN in outcomes:
            status = Status.NEEDS_INFORMATION
        else:
            status = Status.ELIGIBLE
        return SchemeResult(scheme, self.academic_year, status, results)

    def rule(self, rule: Rule) -> RuleResult:
        context = self.context | self._parameter_values(rule)
        title = rule.title.format_map(context)
        if rule.waived_by and self.facts.get(rule.waived_by) is True:
            return RuleResult(rule, Outcome.WAIVED, title, None, None, ())
        missing = tuple(name for name in rule.required_facts(self.facts) if name not in self.facts)
        if missing:
            return RuleResult(rule, Outcome.UNKNOWN, title, None, None, missing)
        if self.simulation.calculate(rule.variable, self.period)[0]:
            return RuleResult(rule, Outcome.PASS, title, None, None, ())
        return RuleResult(
            rule,
            Outcome.FAIL,
            title,
            rule.fail_reason.format_map(context),
            rule.remedy.format_map(context) if rule.remedy else None,
            (),
        )

    def _parameter_values(self, rule: Rule) -> dict[str, str]:
        values = {}
        for name, path in rule.parameter_paths(self.facts).items():
            node = self.parameters
            for part in path.split("."):
                node = getattr(node, part)
            values[name] = format_inr(node) if path.endswith("income_ceiling") else f"{node:g}"
        return values

    def _display_facts(self) -> dict[str, str]:
        specs = fact_specs()
        context = {}
        for name, value in self.facts.items():
            spec = specs[name]
            if name == "family_income":
                context[name] = format_inr(value)
            elif name.endswith("_percent"):
                context[name] = f"{value:g}%"
            elif spec.kind is FactKind.CHOICE:
                context[name] = next(c.label for c in spec.choices if c.key == value)
            elif spec.kind is FactKind.DATE:
                context[name] = f"{value.day} {value:%B %Y}"
            else:
                context[name] = str(value)
        if "date_of_birth" in self.facts:
            age = self.simulation.calculate("age_on_1_july", self.period)[0]
            context["age_on_1_july"] = str(int(age))
        return context


def format_inr(amount: float) -> str:
    """Format rupees with Indian digit grouping, e.g. 250000 -> ₹2,50,000."""
    whole = f"{round(amount):d}"
    if len(whole) <= 3:
        return f"₹{whole}"
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return "₹" + ",".join([*groups, tail])


def _coerce(spec: FactSpec, value: Any) -> Any:
    if spec.kind is FactKind.BOOLEAN:
        if not isinstance(value, bool):
            raise FactError(f"{spec.name} must be true or false")
        return value
    if spec.kind is FactKind.NUMBER:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FactError(f"{spec.name} must be a number")
        if value < 0:
            raise FactError(f"{spec.name} cannot be negative")
        return float(value)
    if spec.kind is FactKind.DATE:
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError) as error:
            raise FactError(f"{spec.name} must be a date in YYYY-MM-DD format") from error
    if value not in {choice.key for choice in spec.choices}:
        raise FactError(f"{spec.name} must be one of: {', '.join(c.key for c in spec.choices)}")
    return value


def _to_openfisca(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, OpenFiscaEnum):
        return value.name
    return value
