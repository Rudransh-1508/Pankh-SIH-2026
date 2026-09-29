import pytest

from pankh_rules import (
    SCHEMES,
    FactError,
    Status,
    UnsupportedAcademicYear,
    evaluate,
    fact_specs,
    next_facts,
    validate_facts,
)
from pankh_rules.engine import format_inr
from pankh_rules.system import pankh_system


@pytest.mark.parametrize(
    ("amount", "text"),
    [(0, "₹0"), (999, "₹999"), (1000, "₹1,000"), (250000, "₹2,50,000"), (12345678, "₹1,23,45,678")],
)
def test_format_inr(amount, text):
    assert format_inr(amount) == text


def test_validate_facts_rejects_unknown_names():
    with pytest.raises(FactError, match="Unknown fact"):
        validate_facts({"caste": "ST"})


@pytest.mark.parametrize(
    ("facts", "message"),
    [
        ({"family_income": "lots"}, "must be a number"),
        ({"family_income": True}, "must be a number"),
        ({"family_income": -1}, "cannot be negative"),
        ({"is_scheduled_tribe": "yes"}, "true or false"),
        ({"date_of_birth": "14/03/1998"}, "YYYY-MM-DD"),
        ({"education_level": "grade_9"}, "must be one of"),
    ],
)
def test_validate_facts_rejects_wrong_kinds(facts, message):
    with pytest.raises(FactError, match=message):
        validate_facts(facts)


def test_none_means_not_known():
    assert validate_facts({"family_income": None}) == {}


def test_rules_start_in_2021_22():
    with pytest.raises(UnsupportedAcademicYear):
        evaluate({}, 2020)


def test_next_facts_skips_schemes_already_ruled_out():
    # Not ST rules out the MoTA Schemes; another scholarship rules out the catalogue ones.
    results = evaluate({"is_scheduled_tribe": False, "holds_other_scholarship": True}, 2026)
    assert all(result.status is Status.NOT_ELIGIBLE for result in results)
    assert next_facts(results) == []


def test_next_facts_prefers_facts_that_settle_more_schemes():
    asked = next_facts(evaluate({"is_scheduled_tribe": True}, 2026))
    assert asked[0] == "education_level"
    assert asked.index("education_level") < asked.index("net_jrf_qualified")


def test_every_rule_is_wired_to_real_variables_parameters_and_facts():
    system = pankh_system()
    specs = fact_specs()
    for scheme in SCHEMES.values():
        for rule in scheme.rules:
            assert rule.variable in system.variables, rule.id
            for facts in ({}, {"education_level": "postgraduate"}, {"education_level": "phd"}):
                assert set(rule.required_facts(facts)) <= set(specs), rule.id
                for path in rule.parameter_paths(facts).values():
                    node = system.parameters("2026-07-01")
                    for part in path.split("."):
                        node = getattr(node, part)
            if rule.waived_by:
                assert rule.waived_by in specs, rule.id


def test_every_rule_variable_belongs_to_a_rule():
    rule_variables = {rule.variable for scheme in SCHEMES.values() for rule in scheme.rules}
    defined = {name for name in pankh_system().variables if "__" in name}
    assert defined == rule_variables


def test_every_fact_is_asked_in_every_language():
    from pankh_rules.questions import LANGUAGES

    for spec in fact_specs().values():
        assert set(spec.question) == set(LANGUAGES), spec.name
        assert all(text.strip() for text in spec.question.values()), spec.name
        if spec.help:
            assert set(spec.help) == set(LANGUAGES), spec.name
        for choice in spec.choices:
            assert set(choice.labels) == set(LANGUAGES), (spec.name, choice.key)


def test_gating_facts_are_asked_first():
    asked = next_facts(evaluate({}, 2026))
    assert asked[:3] == ["is_scheduled_tribe", "education_level", "studies_abroad"]
