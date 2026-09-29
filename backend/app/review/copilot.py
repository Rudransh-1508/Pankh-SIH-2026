"""The reviewer copilot: what a case is about, the exact mismatch, and what to look at.

It reads only the case's own records and past decisions on similar cases. It never suggests a
decision: the Reviewer decides, and the copilot's job is to make that quick and well-founded.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from rapidfuzz.distance import JaroWinkler

from app.verification.names import name_key

SAME_WORD = 0.9


@dataclass(frozen=True)
class WordPair:
    on_document: str | None
    on_aadhaar: str | None
    note: str


@dataclass(frozen=True)
class Precedent:
    confirmed: int
    returned: int
    """Decided cases of the same kind in the same state."""


@dataclass(frozen=True)
class Summary:
    headline: str
    points: list[str] = field(default_factory=list)
    look_at: list[str] = field(default_factory=list)
    words: list[WordPair] = field(default_factory=list)
    precedent: Precedent | None = None


def _words(name: str) -> list[str]:
    return [w for w in re.split(r"\s+", name.strip()) if w]


def word_differences(on_document: str, on_aadhaar: str) -> list[WordPair]:
    """Pair the words of two names and say how each pair differs, as match_names sees them."""
    left, right = _words(on_document), _words(on_aadhaar)
    left_keys = {w: " ".join(name_key(w)) for w in left}
    right_keys = {w: " ".join(name_key(w)) for w in right}
    pairs: list[WordPair] = []
    remaining = [w for w in right if right_keys[w]]
    for word in left:
        key = left_keys[word]
        if not key:
            pairs.append(WordPair(word, None, "a title, which is ignored"))
            continue
        if not remaining:
            pairs.append(WordPair(word, None, "only on the document"))
            continue
        best = max(remaining, key=lambda other: JaroWinkler.similarity(key, right_keys[other]))
        similarity = JaroWinkler.similarity(key, right_keys[best])
        remaining.remove(best)
        if word.casefold() == best.casefold():
            note = "same"
        elif key == right_keys[best]:
            note = "spelt differently, sounds the same"
        elif similarity >= SAME_WORD:
            note = f"close spelling ({round(similarity * 100)}% alike)"
        else:
            note = f"different word ({round(similarity * 100)}% alike)"
        pairs.append(WordPair(word, best, note))
    for word in right:
        if not right_keys[word]:
            pairs.append(WordPair(None, word, "a title, which is ignored"))
        elif word in remaining:
            pairs.append(WordPair(None, word, "only on Aadhaar"))
    return pairs


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int | float):
        return f"{value:,.0f}" if float(value).is_integer() else f"{value:,}"
    if (day := _date(value)) is not None:
        return f"{day:%d %B %Y}"
    return str(value)


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _dob_points(given: Any, confirmed: Any) -> list[str]:
    a, b = _date(given), _date(confirmed)
    if not a or not b:
        return []
    points = [f"The dates are {abs((a - b).days)} days apart."]
    if a.day == b.month and a.month == b.day:
        points.append("Day and month are swapped: a common data-entry slip.")
    elif a.year != b.year and (a.month, a.day) == (b.month, b.day):
        points.append(f"Only the year differs ({a.year} and {b.year}).")
    return points


_LOOK_AT = {
    "name_mismatch": [
        "Whether the differing word is a spelling of the same name, a title, or a surname "
        "added or dropped at marriage.",
        "The father's name and address on the certificate, if they match the student's.",
    ],
    "dob_mismatch": [
        "Which record is original: school records usually set the date on later certificates.",
    ],
    "stale_document": [
        "The financial year printed on the certificate, against the year the session needs.",
    ],
    "paper_certificate": [
        "The seal and signature of the issuing office, and that the office is in the student's "
        "district.",
        "The certificate number's format for that office, and the date of issue.",
        "The name on the photo against the student's Aadhaar name.",
    ],
    "unlinked_identity": [
        "The name in the register against the name the student gave, and against the photo.",
    ],
    "uploaded_document": [
        "The percentage on the photo, and that the marksheet is from the student's institution.",
    ],
    "not_scheduled_tribe": [
        "The category printed on the certificate. Only an ST certificate qualifies.",
    ],
    "value_conflict": [
        "Which value is right: the certificate is used unless it is wrong.",
    ],
}


def summarise(
    kind: str,
    fact_name: str | None,
    evidence: dict[str, Any],
    facts: dict[str, dict[str, Any]],
    photo_fields: dict[str, Any] | None,
    precedent: Precedent | None,
) -> Summary:
    points: list[str] = []
    words: list[WordPair] = []
    fact = facts.get(fact_name or "")
    if fact is not None:
        state = "confirmed" if fact["verified"] else "not yet confirmed"
        points.append(f"The student's value for this is {_display(fact['value'])}, {state}.")

    headline = {
        "name_mismatch": "The names do not clearly match",
        "dob_mismatch": "The dates of birth differ",
        "stale_document": "The certificate is for the wrong year",
        "paper_certificate": "A paper certificate no register could confirm",
        "unlinked_identity": "A genuine certificate, not yet tied to the student",
        "uploaded_document": "A photographed marksheet to confirm",
        "not_scheduled_tribe": "The certificate is not for a Scheduled Tribe",
        "value_conflict": "The student's answer and the certificate differ",
        "unreadable_document": "A document could not be read",
    }.get(kind, kind.replace("_", " ").capitalize())

    on_document = evidence.get("name_on_document") or evidence.get("name_in_register")
    on_aadhaar = evidence.get("name_on_aadhaar")
    if on_document and on_aadhaar:
        words = word_differences(on_document, on_aadhaar)
        differing = [w for w in words if w.note not in ("same", "a title, which is ignored")]
        if differing:
            points.append(
                "Differs: "
                + "; ".join(
                    f"{w.on_document or '(none)'} / {w.on_aadhaar or '(none)'}: {w.note}"
                    for w in differing
                )
                + "."
            )
        else:
            points.append("Every word of the names matches once titles are set aside.")
    if kind == "dob_mismatch" or ("given" in evidence and fact_name == "date_of_birth"):
        points += _dob_points(evidence.get("given"), evidence.get("confirmed"))
    if kind == "value_conflict":
        points.append(
            f"The student said {_display(evidence.get('given'))}; the certificate says "
            f"{_display(evidence.get('confirmed'))}."
        )
    if photo_fields and "holder_name" in photo_fields and on_aadhaar and not on_document:
        points.append(f"The name read from the photo is {photo_fields['holder_name']}.")
    if precedent and precedent.confirmed + precedent.returned:
        points.append(
            f"Similar cases in this state: {precedent.confirmed} confirmed, "
            f"{precedent.returned} returned to the student."
        )
    return Summary(headline, points, _LOOK_AT.get(kind, []), words, precedent)
