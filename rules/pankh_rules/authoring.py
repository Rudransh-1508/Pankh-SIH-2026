"""Drafting Rule changes from a new Guideline, for a ministry official to approve.

A Guideline's text is searched for the figures Rules depend on (income ceilings, minimum marks,
age limits), each with the sentence it came from. Each figure is set against the Scheme's current
Parameter: a different value becomes a proposed change, the same value confirms the Rule still
holds. Nothing changes until a person approves a draft, and an approved draft becomes a change to
the Parameter file, reviewed and tested like any other code.
"""

import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import yaml

PARAMETERS = Path(__file__).parent / "parameters"

# What each Parameter unit looks like in Guideline text.
UNITS = {"currency-INR": "income", "percent": "percent", "year": "age"}


@dataclass(frozen=True)
class Parameter:
    path: str
    """Like "nos.max_age.phd"."""
    scheme_id: str
    description: str
    unit: str
    reference: str
    value: Any
    since: date

    @property
    def file(self) -> Path:
        return PARAMETERS.joinpath(*self.path.split(".")).with_suffix(".yaml")


@dataclass(frozen=True)
class Figure:
    kind: str  # income | percent | age
    value: float
    page: int
    excerpt: str
    context: str = ""
    """The words just before the figure: in a table, its row so far."""


@dataclass(frozen=True)
class Draft:
    parameter: Parameter
    figure: Figure
    changed: bool


def _latest(values: dict[date, dict[str, Any]]) -> tuple[date, Any]:
    since = max(values)
    return since, values[since]["value"]


@cache
def parameters() -> tuple[Parameter, ...]:
    found = []
    for file in sorted(PARAMETERS.rglob("*.yaml")):
        data = yaml.safe_load(file.read_text())
        if "unit" not in data:
            continue
        parts = file.relative_to(PARAMETERS).with_suffix("").parts
        since, value = _latest(data["values"])
        found.append(
            Parameter(
                ".".join(parts),
                parts[0],
                data["description"],
                data["unit"],
                data.get("reference", ""),
                value,
                since,
            )
        )
    return tuple(found)


_ABBREVIATIONS = r"(?<!\bPh)(?<!\bRs)(?<!\bNo)(?<!\bSl)(?<!\bi\.e)(?<!\b[A-Z])"


def _sentences(text: str) -> list[str]:
    # PDF text breaks lines mid-sentence; join them, then split on sentence ends and list items.
    flowing = re.sub(r"\s*\n\s*", " ", text)
    parts = re.split(_ABBREVIATIONS + r"(?<=[.;])\s+(?=[A-Z(]|[ivx]+\.\s)", flowing)
    return [p.strip() for p in parts if p.strip()]


def _context(sentence: str, start: int) -> str:
    """The text before a figure, from the start of its table row if it is in one."""
    before = sentence[:start]
    rows = list(re.finditer(r"(?:^|\s)\d\s+(?=[A-Z])", before))
    return before[rows[-1].end() :] if rows else before


_RUPEES = r"(?:rs\.?|₹|inr|rupees)\s*"
_LAKH = re.compile(_RUPEES + r"([0-9]+(?:\.[0-9]+)?)\s*lakh", re.IGNORECASE)
_AMOUNT = re.compile(_RUPEES + r"([0-9][0-9,]{3,})", re.IGNORECASE)
_PERCENT = re.compile(r"([0-9]{2}(?:\.[0-9]+)?)\s*(?:%|per\s?cent)", re.IGNORECASE)
_AGE = re.compile(r"([0-9]{2})\s*years", re.IGNORECASE)


def extract_figures(pages: list[str]) -> list[Figure]:
    """Every income, marks and age figure in the text, with the sentence it came from."""
    figures = []
    for number, text in enumerate(pages, 1):
        page_text = text.casefold()
        for sentence in _sentences(text):
            lowered = sentence.casefold()
            if "income" in lowered:
                for match in _LAKH.finditer(sentence):
                    value = float(match.group(1)) * 100_000
                    figures.append(Figure("income", value, number, sentence, sentence))
                for match in _AMOUNT.finditer(sentence):
                    value = float(match.group(1).replace(",", ""))
                    figures.append(Figure("income", value, number, sentence, sentence))
            # Tables name what their figures are in a heading, so these cues are read per page.
            for kind, pattern, cue, low, high in (
                ("percent", _PERCENT, r"marks|percentage|aggregate|grade", 30, 100),
                ("age", _AGE, r"\bage\b|aged", 18, 60),
            ):
                if not re.search(cue, page_text):
                    continue
                for match in pattern.finditer(sentence):
                    value = float(match.group(1))
                    if low <= value <= high:
                        context = _context(sentence, match.start())
                        figures.append(Figure(kind, value, number, sentence, context))
    return figures


# Words that say which course a figure is for, by how Guidelines and Parameters spell them.
_QUALIFIERS = {
    "master": ("master",),
    "bachelor": ("bachelor", "graduat"),
    "phd": ("ph.d", "phd", "ph. d"),
    "postdoc": ("post-doc", "postdoc", "post doc"),
}


def _qualifiers_in(text: str) -> list[tuple[int, str]]:
    text = text.casefold()
    found = []
    for name, spellings in _QUALIFIERS.items():
        positions = [text.find(s) for s in spellings if s in text]
        if positions:
            found.append((min(positions), name))
    return sorted(found)


def _fit(parameter: Parameter, figure: Figure) -> int:
    """How well a figure fits a Parameter: 2 when its row or sentence is about the Parameter's
    course, 1 when it mentions it, 0 otherwise."""
    wanted = {name for _, name in _qualifiers_in(parameter.path + " " + parameter.description)}
    if not wanted:
        return 0
    found = _qualifiers_in(figure.context)
    if found and found[0][1] in wanted:
        return 2
    return 1 if any(name in wanted for _, name in found) else 0


def draft_changes(scheme_id: str, pages: list[str]) -> list[Draft]:
    """For each of the Scheme's Parameters, the best-fitting figure in the Guideline, if any."""
    figures = extract_figures(pages)
    drafts = []
    for parameter in (p for p in parameters() if p.scheme_id == scheme_id):
        kind = UNITS.get(parameter.unit)
        candidates = [f for f in figures if f.kind == kind]
        if not candidates:
            continue
        # Prefer the closest-fitting sentence; among equals, the one that confirms the Rule,
        # then the first in the document.
        best = max(
            candidates,
            key=lambda f: (_fit(parameter, f), f.value == float(parameter.value), -f.page),
        )
        drafts.append(Draft(parameter, best, changed=best.value != float(parameter.value)))
    return drafts


def patched(parameter: Parameter, value: float, effective_from: date, reference: str) -> str:
    """The Parameter file with the new value from `effective_from`, citing its source."""
    data = yaml.safe_load(parameter.file.read_text())
    typed = int(value) if float(value).is_integer() else value
    data["values"][effective_from] = {"value": typed}
    data["values"] = dict(sorted(data["values"].items()))
    data["reference"] = f"{data.get('reference', '')}; {reference}".lstrip("; ")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
