from datetime import date
from pathlib import Path

import pytest
import yaml

from pankh_rules.authoring import draft_changes, extract_figures, parameters, patched

CACHE = Path(__file__).resolve().parents[1] / ".cache" / "sources"


def test_a_revised_income_ceiling_becomes_a_proposed_change():
    pages = [
        "Central Sector Scheme of Scholarship for College and University Students.\n"
        "v. Students with gross parental/family income upto Rs. 6 lakh per annum are\n"
        "eligible for scholarship under the scheme."
    ]
    (draft,) = draft_changes("csss", pages)
    assert draft.parameter.path == "csss.income_ceiling"
    assert (draft.parameter.value, draft.figure.value, draft.changed) == (450000, 600000.0, True)
    assert draft.figure.page == 1
    assert "Rs. 6 lakh per annum" in draft.figure.excerpt


def test_table_rows_are_matched_to_their_course():
    pages = [
        "Qualification\nSr. No. Course Marks Maximum Age as on 1st July of selection year\n"
        "1 Post-Doctoral 55% marks in Master's Degree with Ph.D. 40 years\n"
        "2 Ph.D 55% marks in Master's Degree 35 years\n"
        "3 Master's Degree 60% marks in Bachelor's Degree 32 years"
    ]
    drafts = {d.parameter.path: d for d in draft_changes("nos", pages)}
    assert drafts["nos.max_age.postdoc"].figure.value == 40
    assert drafts["nos.max_age.postdoc"].changed
    assert drafts["nos.max_age.phd"].figure.value == 35
    assert not drafts["nos.max_age.phd"].changed
    assert drafts["nos.max_age.masters"].figure.value == 32


def test_amounts_are_read_in_lakh_and_in_full():
    figures = extract_figures(["Total family income should not exceed Rs. 2,50,000 per annum."])
    assert [(f.kind, f.value) for f in figures] == [("income", 250000.0)]


def test_an_approved_change_adds_a_dated_value_and_its_source():
    parameter = next(p for p in parameters() if p.path == "csss.income_ceiling")
    text = patched(
        parameter, 600000.0, date(2027, 7, 1), "csss-guidelines-2027, page 2, para 4 (v)"
    )
    data = yaml.safe_load(text)
    assert data["values"][date(2022, 7, 1)] == {"value": 450000}
    assert data["values"][date(2027, 7, 1)] == {"value": 600000}
    assert data["reference"].endswith("; csss-guidelines-2027, page 2, para 4 (v)")


@pytest.mark.skipif(not CACHE.exists(), reason="official sources not fetched")
def test_every_figure_found_in_the_cited_guidelines_matches_the_rules():
    import pdfplumber

    for scheme, source in [
        ("csss", "csss-guidelines-2022"),
        ("nos", "nos-guidelines-2022"),
        ("nfst", "nfs-guidelines-2022"),
        ("pragati", "pragati-degree-guidelines-2021"),
    ]:
        with pdfplumber.open(CACHE / f"{source}.pdf") as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        drafts = draft_changes(scheme, pages)
        assert drafts, source
        assert [d.parameter.path for d in drafts if d.changed] == [], source
