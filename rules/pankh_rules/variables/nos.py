import numpy

from pankh_rules.variables._base import RuleVariable, holds_no_other_mota_award, level_in
from pankh_rules.variables.facts import EducationLevel, MotaAward


class nos__scheduled_tribe(RuleVariable):
    def formula(student, period):
        return student("is_scheduled_tribe", period)


class nos__covered_course_abroad(RuleVariable):
    def formula(student, period, parameters):
        covered = level_in(student, period, EducationLevel.postgraduate, EducationLevel.phd)
        if parameters(period).nos.postdoc_covered:
            covered = covered + level_in(student, period, EducationLevel.postdoc)
        return covered * student("studies_abroad", period)


class nos__admission_offer(RuleVariable):
    def formula(student, period):
        return student("has_overseas_admission_offer", period)


class nos__qualifying_marks(RuleVariable):
    def formula(student, period, parameters):
        minimum = parameters(period).nos.min_marks_percent
        for_masters = level_in(student, period, EducationLevel.postgraduate)
        marks = numpy.where(
            for_masters,
            student("bachelors_marks_percent", period),
            student("masters_marks_percent", period),
        )
        return student("overseas_admission_in_qs_top_1000", period) + (marks >= minimum)


class nos__age_limit(RuleVariable):
    def formula(student, period, parameters):
        limits = parameters(period).nos.max_age
        level = student("education_level", period)
        max_age = numpy.select(
            [
                level == EducationLevel.postgraduate,
                level == EducationLevel.phd,
                level == EducationLevel.postdoc,
            ],
            [limits.masters, limits.phd, limits.postdoc],
            default=0,
        )
        return student("age_on_1_july", period) <= max_age


class nos__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        ceiling = parameters(period).nos.income_ceiling
        return student("is_orphan_supported_by_guardian", period) + (
            student("family_income", period) <= ceiling
        )


class nos__one_child_per_family(RuleVariable):
    def formula(student, period):
        return ~student("sibling_received_nos", period)


class nos__first_award(RuleVariable):
    def formula(student, period):
        return ~student("previously_received_nos", period)


class nos__no_other_mota_award(RuleVariable):
    def formula(student, period):
        return holds_no_other_mota_award(student, period, MotaAward.nos)


class nos__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return ~student("holds_other_scholarship", period)
