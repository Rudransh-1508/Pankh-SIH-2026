from pankh_rules.variables._base import RuleVariable, holds_no_other_mota_award, level_in
from pankh_rules.variables.facts import EducationLevel, MotaAward


class pre_matric__scheduled_tribe(RuleVariable):
    def formula(student, period):
        return student("is_scheduled_tribe", period)


class pre_matric__class_ix_or_x(RuleVariable):
    def formula(student, period):
        in_class = level_in(student, period, EducationLevel.class_9, EducationLevel.class_10)
        return in_class * ~student("studies_abroad", period)


class pre_matric__recognised_school(RuleVariable):
    def formula(student, period):
        return student("institution_recognised", period)


class pre_matric__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        ceiling = parameters(period).pre_matric.income_ceiling
        return student("is_orphan_supported_by_guardian", period) + (
            student("family_income", period) <= ceiling
        )


class pre_matric__aadhaar_seeded_bank_account(RuleVariable):
    def formula(student, period):
        return student("has_aadhaar_seeded_bank_account", period)


class pre_matric__no_other_mota_award(RuleVariable):
    def formula(student, period):
        return holds_no_other_mota_award(student, period, MotaAward.pre_matric)


class pre_matric__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return ~student("holds_other_scholarship", period)
