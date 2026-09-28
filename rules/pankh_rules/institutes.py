import csv
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
