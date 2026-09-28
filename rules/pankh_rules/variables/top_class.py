from pankh_rules.variables._base import RuleVariable, holds_no_other_mota_award, level_in
from pankh_rules.variables.facts import EducationLevel, MotaAward


class top_class__scheduled_tribe(RuleVariable):
    def formula(student, period):
        return student("is_scheduled_tribe", period)


class top_class__graduate_or_postgraduate_course(RuleVariable):
    def formula(student, period):
        return level_in(student, period, EducationLevel.undergraduate, EducationLevel.postgraduate)


class top_class__admitted_to_notified_institute(RuleVariable):
    def formula(student, period):
        return student("admitted_to_top_class_institute", period)


class top_class__not_management_quota(RuleVariable):
    def formula(student, period):
        return ~student("admitted_via_management_quota", period)


class top_class__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        ceiling = parameters(period).top_class.income_ceiling
        return student("is_orphan_supported_by_guardian", period) + (
            student("family_income", period) <= ceiling
        )


class top_class__no_other_mota_award(RuleVariable):
    def formula(student, period):
        return holds_no_other_mota_award(student, period, MotaAward.top_class)


class top_class__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return ~student("holds_other_scholarship", period)
