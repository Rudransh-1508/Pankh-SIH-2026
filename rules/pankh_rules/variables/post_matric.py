from pankh_rules.variables._base import RuleVariable, holds_no_other_mota_award, level_in
from pankh_rules.variables.facts import EducationLevel, MotaAward

POST_MATRIC_LEVELS = (
    EducationLevel.class_11,
    EducationLevel.class_12,
    EducationLevel.diploma,
    EducationLevel.undergraduate,
    EducationLevel.postgraduate,
    EducationLevel.mphil,
    EducationLevel.phd,
    EducationLevel.postdoc,
)


class post_matric__scheduled_tribe(RuleVariable):
    def formula(student, period):
        return student("is_scheduled_tribe", period)


class post_matric__post_matric_course_in_india(RuleVariable):
    def formula(student, period):
        return level_in(student, period, *POST_MATRIC_LEVELS) * ~student("studies_abroad", period)


class post_matric__recognised_institution(RuleVariable):
    def formula(student, period):
        return student("institution_recognised", period)


class post_matric__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        return student("family_income", period) <= parameters(period).post_matric.income_ceiling


class post_matric__not_repeating_stage(RuleVariable):
    def formula(student, period):
        return ~student("repeating_stage_in_other_subject", period)


class post_matric__not_at_top_class_institute(RuleVariable):
    def formula(student, period):
        return ~student("admitted_to_top_class_institute", period)


class post_matric__no_other_mota_award(RuleVariable):
    def formula(student, period):
        return holds_no_other_mota_award(student, period, MotaAward.post_matric)


class post_matric__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return ~student("holds_other_scholarship", period)
