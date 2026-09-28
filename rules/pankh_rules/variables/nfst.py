from pankh_rules.variables._base import RuleVariable, holds_no_other_mota_award, level_in
from pankh_rules.variables.facts import EducationLevel, MotaAward


class nfst__scheduled_tribe(RuleVariable):
    def formula(student, period):
        return student("is_scheduled_tribe", period)


class nfst__research_course_in_india(RuleVariable):
    def formula(student, period):
        research = level_in(student, period, EducationLevel.mphil, EducationLevel.phd)
        return research * ~student("studies_abroad", period)


class nfst__masters_marks(RuleVariable):
    def formula(student, period, parameters):
        minimum = parameters(period).nfst.min_masters_marks_percent
        return student("masters_marks_percent", period) >= minimum


class nfst__age_limit(RuleVariable):
    def formula(student, period, parameters):
        return student("age_on_1_july", period) <= parameters(period).nfst.max_age


class nfst__eligible_institution(RuleVariable):
    def formula(student, period):
        return student("institution_eligible_for_fellowship", period)


class nfst__net_qualified(RuleVariable):
    def formula(student, period, parameters):
        required = parameters(period).nfst.net_jrf_required
        return student("net_jrf_qualified", period) + (not required)


class nfst__no_other_mota_award(RuleVariable):
    def formula(student, period):
        return holds_no_other_mota_award(student, period, MotaAward.nfst)


class nfst__no_other_scholarship(RuleVariable):
    def formula(student, period):
        return ~student("holds_other_scholarship", period)
