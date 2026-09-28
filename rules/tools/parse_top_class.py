"""Turn the official Top Class institute list PDF into pankh_rules/data/top_class_institutes.csv.

Usage: uv run --group tools python rules/tools/parse_top_class.py
Run fetch_sources.py first.
"""

import csv
import re
import sys
from pathlib import Path

import pdfplumber

RULES_DIR = Path(__file__).resolve().parent.parent
SOURCE = RULES_DIR / ".cache" / "sources" / "top-class-institutes-2023.pdf"
OUTPUT = RULES_DIR / "pankh_rules" / "data" / "top_class_institutes.csv"
EXPECTED_COUNT = 265


def main() -> int:
    rows: dict[int, dict[str, str]] = {}
    with pdfplumber.open(SOURCE) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for table in page.extract_tables():
                for cells in table:
                    serial = (cells[0] or "").strip()
                    if not serial.isdigit():
                        continue
                    rows[int(serial)] = {
                        "serial": serial,
                        "name": _clean(cells[1]),
                        "location": _clean(cells[2]),
                        "state": _clean(cells[3]),
                        "courses": _clean(cells[4]),
                        "source_page": str(page_number),
                    }
    if sorted(rows) != list(range(1, EXPECTED_COUNT + 1)):
        missing = sorted(set(range(1, EXPECTED_COUNT + 1)) - set(rows))
        print(f"Expected serials 1..{EXPECTED_COUNT}; missing {missing}", file=sys.stderr)
        return 1
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[1]))
        writer.writeheader()
        writer.writerows(rows[serial] for serial in sorted(rows))
    print(f"Wrote {len(rows)} institutes to {OUTPUT.relative_to(RULES_DIR)}")
    return 0


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").replace(" ,", ",").strip()


if __name__ == "__main__":
    sys.exit(main())
