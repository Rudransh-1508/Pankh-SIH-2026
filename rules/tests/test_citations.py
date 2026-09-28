import pytest

from pankh_rules import SCHEMES, search_top_class, sources, top_class_institutes


def test_every_citation_points_at_a_page_that_exists():
    for scheme in SCHEMES.values():
        for item in (*scheme.rules, *scheme.benefits):
            source = sources()[item.citation.source_id]
            assert 1 <= item.citation.page <= source.pages


def test_citation_links_open_the_cited_page():
    rule = SCHEMES["nfst"].rules[3]
    assert rule.citation.url.endswith(".pdf#page=5")


def test_top_class_list_has_all_265_institutes():
    institutes = top_class_institutes()
    assert sorted(institutes) == list(range(1, 266))
    assert institutes[1].name == "Indian Institute of Technology Delhi"
    assert institutes[265].name == "Indian Institute of Management, Jammu"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("nit rourkela", "National Institute of Technology Rourkela"),
        ("IIT Delhi", "Indian Institute of Technology Delhi"),
        ("aiims deoghar", "All India Institute of Medical Sciences, Deoghar"),
        ("iim jammu", "Indian Institute of Management, Jammu"),
        ("technology kharagpur", "Indian Institute of Technology Kharagpur"),
    ],
)
def test_search_understands_abbreviations(query, expected):
    names = [institute.name for institute in search_top_class(query)]
    assert expected in names


def test_search_needs_every_word():
    assert search_top_class("iit atlantis") == []
