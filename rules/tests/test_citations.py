from pankh_rules import SCHEMES, sources, top_class_institutes


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
