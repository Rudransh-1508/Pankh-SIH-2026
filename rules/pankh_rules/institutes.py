import csv
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from pankh_rules.citations import Citation, cite

DATA_FILE = Path(__file__).resolve().parent / "data" / "top_class_institutes.csv"


@dataclass(frozen=True)
class TopClassInstitute:
    """An institute notified for the Top Class scholarship, from the ministry's official list."""

    id: int
    name: str
    location: str
    state: str
    courses: str
    citation: Citation


@cache
def top_class_institutes() -> dict[int, TopClassInstitute]:
    with DATA_FILE.open(newline="") as handle:
        return {
            int(row["serial"]): TopClassInstitute(
                id=int(row["serial"]),
                name=row["name"],
                location=row["location"],
                state=row["state"],
                courses=row["courses"],
                citation=cite(
                    "top-class-institutes-2023", int(row["source_page"]), f"S.No. {row['serial']}"
                ),
            )
            for row in csv.DictReader(handle)
        }


_MINOR_WORDS = {"of", "and", "the", "for", "in", "at"}


def _initials(name: str) -> str:
    """'National Institute of Technology Rourkela' -> 'nitr'."""
    words = re.findall(r"[a-z]+", name.lower())
    return "".join(word[0] for word in words if word not in _MINOR_WORDS)


def search_top_class(query: str, limit: int = 20) -> list[TopClassInstitute]:
    """Institutes matching every word of the query.

    A word matches the name, location or state, or, if it has three or more letters, the
    institute's initials, so students can type "NIT Rourkela", "IIT Delhi" or "AIIMS".
    """
    words = re.findall(r"[a-z0-9]+", query.lower())
    matches = []
    for institute in top_class_institutes().values():
        text = f"{institute.name} {institute.location} {institute.state}".lower()
        initials = _initials(institute.name)
        if all(word in text or (len(word) >= 3 and word in initials) for word in words):
            matches.append(institute)
    return matches[:limit]
