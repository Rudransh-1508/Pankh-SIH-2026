"""One fully eligible Student per Scheme, as described by that Scheme's Guidelines."""

import pytest

from pankh_rules import SCHEMES, Outcome, Status, evaluate

SCHEME_IDS = list(SCHEMES)


def _result(facts, scheme_id, year=2026):
    (result,) = evaluate(facts, year, [scheme_id])
    return result


@pytest.mark.parametrize("scheme_id", SCHEME_IDS)
def test_eligible_profile(profiles, scheme_id):
    result = _result(profiles[scheme_id], scheme_id)
    failing = [(r.rule.id, r.outcome) for r in result.rules if r.outcome is not Outcome.PASS]
    assert result.status is Status.ELIGIBLE, failing


@pytest.mark.parametrize("scheme_id", SCHEME_IDS)
def test_every_rule_unknown_without_facts(scheme_id):
    result = _result({}, scheme_id)
    assert result.status is Status.NEEDS_INFORMATION
    assert all(r.outcome is Outcome.UNKNOWN for r in result.rules)
    assert all(r.missing_facts for r in result.rules)
