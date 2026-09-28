"""Specific Rules, including how they change across academic years."""

from pankh_rules import Outcome, Status, evaluate


def _rule(facts, rule_id, year=2026):
    scheme_id = rule_id.split(".")[0]
    (result,) = evaluate(facts, year, [scheme_id])
    return next(r for r in result.rules if r.rule.id == rule_id)


def test_income_at_the_ceiling_passes_and_above_fails(profiles):
    facts = profiles["post_matric"]
    at_ceiling = _rule(facts | {"family_income": 250000}, "post_matric.income_within_ceiling")
    assert at_ceiling.outcome is Outcome.PASS
    above = _rule(facts | {"family_income": 250001}, "post_matric.income_within_ceiling")
    assert above.outcome is Outcome.FAIL
    assert above.reason == "Your family income of ₹2,50,001 is above the limit of ₹2,50,000."


def test_orphan_supported_by_guardian_waives_income(profiles):
    orphan = {"family_income": 900000, "is_orphan_supported_by_guardian": True}
    facts = profiles["pre_matric"] | orphan
    assert _rule(facts, "pre_matric.income_within_ceiling").outcome is Outcome.WAIVED


def test_post_matric_has_no_orphan_waiver(profiles):
    orphan = {"family_income": 900000, "is_orphan_supported_by_guardian": True}
    facts = profiles["post_matric"] | orphan
    assert _rule(facts, "post_matric.income_within_ceiling").outcome is Outcome.FAIL


def test_waiver_does_not_need_the_waived_fact():
    rule = _rule({"is_orphan_supported_by_guardian": True}, "top_class.income_within_ceiling")
    assert rule.outcome is Outcome.WAIVED


def test_net_is_required_for_nfst_only_from_2025_26(profiles):
    facts = profiles["nfst"] | {"net_jrf_qualified": False}
    assert _rule(facts, "nfst.net_qualified", year=2024).outcome is Outcome.PASS
    assert _rule(facts, "nfst.net_qualified", year=2025).outcome is Outcome.FAIL


def test_nos_postdoc_is_covered_until_2025_26(profiles):
    postdoc = {"education_level": "postdoc", "masters_marks_percent": 70}
    facts = profiles["nos"] | postdoc
    assert _rule(facts, "nos.covered_course_abroad", year=2025).outcome is Outcome.PASS
    assert _rule(facts, "nos.covered_course_abroad", year=2026).outcome is Outcome.FAIL


def test_nos_age_limit_depends_on_course_level(profiles):
    facts = profiles["nos"] | {"date_of_birth": "1992-12-01"}  # 33 on 1 July 2026
    masters = _rule(facts, "nos.age_limit")
    assert masters.outcome is Outcome.FAIL
    assert masters.title == "Aged 32 or under on 1 July"
    assert masters.reason.startswith("You are 33 on 1 July, above the limit of 32")
    phd = _rule(facts | {"education_level": "phd"}, "nos.age_limit")
    assert (phd.outcome, phd.title) == (Outcome.PASS, "Aged 35 or under on 1 July")


def test_age_counts_a_birthday_on_1_july(profiles):
    facts = profiles["nfst"]
    assert _rule(facts | {"date_of_birth": "1990-07-01"}, "nfst.age_limit").outcome is Outcome.PASS
    assert _rule(facts | {"date_of_birth": "1989-07-01"}, "nfst.age_limit").outcome is Outcome.FAIL
    assert _rule(facts | {"date_of_birth": "1989-07-02"}, "nfst.age_limit").outcome is Outcome.PASS


def test_nos_marks_waived_for_qs_top_1000(profiles):
    facts = profiles["nos"] | {"bachelors_marks_percent": 48}
    assert _rule(facts, "nos.qualifying_marks").outcome is Outcome.FAIL
    waived = facts | {"overseas_admission_in_qs_top_1000": True}
    assert _rule(waived, "nos.qualifying_marks").outcome is Outcome.WAIVED


def test_nos_phd_uses_masters_marks(profiles):
    facts = profiles["nos"] | {"education_level": "phd"}
    rule = _rule(facts, "nos.qualifying_marks")
    assert (rule.outcome, rule.missing_facts) == (Outcome.UNKNOWN, ("masters_marks_percent",))


def test_only_one_mota_award_at_a_time(profiles):
    facts = profiles["top_class"] | {"current_mota_award": "post_matric"}
    rule = _rule(facts, "top_class.no_other_mota_award")
    assert rule.outcome is Outcome.FAIL
    assert "You already hold the Post-Matric Scholarship" in rule.reason
    assert rule.remedy


def test_holding_the_same_scheme_is_a_renewal(profiles):
    facts = profiles["post_matric"] | {"current_mota_award": "post_matric"}
    (result,) = evaluate(facts, 2026, ["post_matric"])
    assert result.status is Status.ELIGIBLE


def test_top_class_students_are_not_on_post_matric(profiles):
    facts = profiles["post_matric"] | {"admitted_to_top_class_institute": True}
    rule = _rule(facts, "post_matric.not_at_top_class_institute")
    assert rule.outcome is Outcome.FAIL
    assert "Top Class" in rule.remedy
