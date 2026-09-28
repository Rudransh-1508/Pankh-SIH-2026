import numpy
from openfisca_core.periods import DateUnit
from openfisca_core.variables import Variable

from pankh_rules.entities import Student


class age_on_1_july(Variable):
    value_type = int
    entity = Student
    definition_period = DateUnit.MONTH
    label = "Age in completed years on 1 July of the academic session"

    def formula(student, period):
        birth = student("date_of_birth", period)
        birth_year = birth.astype("datetime64[Y]").astype(int) + 1970
        birth_month = birth.astype("datetime64[M]").astype(int) % 12 + 1
        birth_day = (birth - birth.astype("datetime64[M]")).astype(int) + 1
        birthday_passed = (birth_month < 7) | ((birth_month == 7) & (birth_day == 1))
        return period.start.year - birth_year - numpy.where(birthday_passed, 0, 1)
