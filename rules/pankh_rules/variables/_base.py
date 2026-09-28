import numpy
from openfisca_core.periods import DateUnit
from openfisca_core.variables import Variable

from pankh_rules.entities import Student
from pankh_rules.variables.facts import EducationLevel, MotaAward


class RuleVariable(Variable):
    """One Rule of one Scheme. True means the Rule is satisfied."""

    value_type = bool
    entity = Student
    definition_period = DateUnit.MONTH


def level_in(student, period, *levels: EducationLevel):
    level = student("education_level", period)
    return numpy.isin(level.decode_to_str(), [lvl.name for lvl in levels])


def holds_no_other_mota_award(student, period, scheme: MotaAward):
    award = student("current_mota_award", period)
    return (award == MotaAward.none) + (award == scheme)
