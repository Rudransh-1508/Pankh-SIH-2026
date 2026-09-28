"""Extract state-wise Pre- and Post-Matric beneficiaries from the ministry's published workbook.

Usage (from backend/): uv run --with openpyxl --with httpx python tools/parse_beneficiaries.py

Source: Annexure I, Pre-Matric and Post-Matric Scholarship fund released, utilised and
beneficiaries, FY 2013-14 to 2025-26, published at https://tribal.nic.in/ScholarshiP.aspx.
The site serves an incomplete certificate chain, so the download is checked by sha256 instead.
"""

import csv
import hashlib
import io
import sys
from pathlib import Path

import httpx
import openpyxl

URL = (
    "https://tribal.nic.in/downloads/scholarship/pre/"
    "AnnexureI-PreMatricnPost-MatricScholarshipFundreleasedUtilizedBeneficiary2013-24to2025-26.xlsx"
)
SHA256 = "79b542a9a2c841a2417a5a7dd4f016d400381ba84a293d838b3132c6c8677bd3"
OUTPUT = (
    Path(__file__).resolve().parent.parent / "app" / "coverage" / "data" / "mota_beneficiaries.csv"
)
SHEETS = {
    "Pre Matric Scholarship Scheme": "pre_matric",
    "Post Matric Scholarship Scheme": "post_matric",
}

# The workbook spells some states differently between sheets; use one name for each.
STATE_NAMES = {
    "A.& N. Islands": "Andaman & Nicobar",
    "Andaman & Nicobar": "Andaman & Nicobar",
    "Jammu & Kashmir": "Jammu & Kashmir",
    "DNH & DD": "Dadra & Nagar Haveli and Daman & Diu",
    "DNH DD": "Dadra & Nagar Haveli and Daman & Diu",
    "Maharashtra*": "Maharashtra",
}


def main() -> int:
    content = httpx.get(
        URL, verify=False, headers={"User-Agent": "Mozilla/5.0"}, timeout=60
    ).content
    if hashlib.sha256(content).hexdigest() != SHA256:
        print(
            "The published workbook has changed. Review it before updating SHA256.", file=sys.stderr
        )
        return 1
    workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    rows = []
    for sheet_name, scheme in SHEETS.items():
        sheet = workbook[sheet_name]
        header = [cell.value for cell in sheet[3]]
        subheader = [cell.value for cell in sheet[4]]
        years = {}
        for column, label in enumerate(header):
            if isinstance(label, str) and label.startswith("F.Y."):
                years[column] = label.removeprefix("F.Y.").strip()
        width = max(years) + 3
        for raw in sheet.iter_rows(min_row=5, values_only=True):
            row = list(raw) + [None] * (width - len(raw))
            state = row[1]
            if not isinstance(state, str) or state.strip().lower() == "total":
                if isinstance(state, str):
                    break
                continue
            state = STATE_NAMES.get(state.strip(), state.strip())
            for column, year in years.items():
                released, utilised, beneficiaries = row[column : column + 3]
                label = subheader[column + 2] if column + 2 < len(subheader) else ""
                estimated = "estimated" in str(label or "").lower()
                if not isinstance(beneficiaries, int | float):
                    continue  # blank or "NA" in the workbook
                rows.append(
                    {
                        "scheme": scheme,
                        "state": state,
                        "financial_year": year,
                        "fund_released_crore": released
                        if isinstance(released, int | float)
                        else "",
                        "utilised_crore": utilised if isinstance(utilised, int | float) else "",
                        "beneficiaries": int(beneficiaries),
                        "estimated": estimated,
                    }
                )
    with OUTPUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
