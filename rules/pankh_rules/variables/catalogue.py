"""Rules of Catalogue Schemes: central schemes open to ST students, shown for discovery."""

from pankh_rules.variables._base import RuleVariable, level_in
from pankh_rules.variables.facts import EducationLevel, Gender, MotaAward


def _no_other_scholarship(student, period):
    """These schemes allow no other scholarship, including a MoTA award."""
    return ~student("holds_other_scholarship", period) * (
        student("current_mota_award", period) == MotaAward.none
    )


class csss__class_12_top_20_percent(RuleVariable):
    def formula(student, period):
        return student("class_12_top_20_percent", period)


class csss__regular_degree_course(RuleVariable):
    def formula(student, period):
        degree = level_in(
            student, period, EducationLevel.undergraduate, EducationLevel.postgraduate
        )
        return degree * ~student("studies_by_distance", period) * ~student("studies_abroad", period)


class csss__recognised_institution(RuleVariable):
    def formula(student, period):
        return student("institution_recognised", period)


class csss__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        return student("family_income", period) <= parameters(period).csss.income_ceiling


class csss__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return _no_other_scholarship(student, period)


class pragati__girl_student(RuleVariable):
    def formula(student, period):
        return student("gender", period) == Gender.female


class pragati__first_year_technical_degree(RuleVariable):
    def formula(student, period):
        return student("aicte_technical_first_year", period) * level_in(
            student, period, EducationLevel.undergraduate
        )


class pragati__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        return student("family_income", period) <= parameters(period).pragati.income_ceiling


class pragati__joined_within_two_years(RuleVariable):
    def formula(student, period):
        return student("joined_within_two_years_of_class_12", period)


class pragati__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return _no_other_scholarship(student, period)


class nmmss__selected_in_exam(RuleVariable):
    def formula(student, period):
        return student("selected_in_nmms_exam", period)


class nmmss__class_ix_to_xii(RuleVariable):
    def formula(student, period):
        school = level_in(
            student,
            period,
            EducationLevel.class_9,
            EducationLevel.class_10,
            EducationLevel.class_11,
            EducationLevel.class_12,
        )
        return school * ~student("studies_abroad", period)


class nmmss__eligible_school(RuleVariable):
    def formula(student, period):
        return student("school_government_aided_or_local_body", period)


class nmmss__income_within_ceiling(RuleVariable):
    def formula(student, period, parameters):
        return student("family_income", period) <= parameters(period).nmmss.income_ceiling


class nmmss__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return _no_other_scholarship(student, period)
