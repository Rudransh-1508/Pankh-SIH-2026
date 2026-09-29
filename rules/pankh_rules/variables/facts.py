"""Facts: the inputs every Rule is judged on.

Each Fact is an OpenFisca input variable evaluated at the month an academic session starts (July).
Labels and documentation here are shown to Students, so they are written in plain language.
"""

from datetime import date

from openfisca_core.indexed_enums import Enum
from openfisca_core.periods import DateUnit
from openfisca_core.variables import Variable

from pankh_rules.entities import Student


class EducationLevel(Enum):
    unknown = "Not given"
    class_9 = "Class IX"
    class_10 = "Class X"
    class_11 = "Class XI"
    class_12 = "Class XII"
    diploma = "Diploma or ITI"
    undergraduate = "Undergraduate (Bachelor's)"
    postgraduate = "Postgraduate (Master's)"
    mphil = "M.Phil"
    phd = "Ph.D"
    postdoc = "Post-doctoral research"


class Gender(Enum):
    unknown = "Not given"
    female = "Female"
    male = "Male"
    other = "Other"


class MotaAward(Enum):
    none = "None"
    pre_matric = "Pre-Matric Scholarship"
    post_matric = "Post-Matric Scholarship"
    top_class = "Top Class Scholarship"
    nfst = "National Fellowship (NFST)"
    nos = "National Overseas Scholarship (NOS)"


class _Fact(Variable):
    entity = Student
    definition_period = DateUnit.MONTH


class is_scheduled_tribe(_Fact):
    value_type = bool
    label = "Belongs to a Scheduled Tribe of their domicile state"
    documentation = (
        "The Student's tribe is notified as a Scheduled Tribe for the state or union territory "
        "they are domiciled in."
    )


class date_of_birth(_Fact):
    value_type = date
    default_value = date(1970, 1, 1)
    label = "Date of birth"


class family_income(_Fact):
    value_type = float
    label = "Annual family income (INR)"
    documentation = (
        "Gross income from all sources of both parents, or of the living parent. For a married "
        "Student, the spouse's income is added. Income of siblings or other relatives is not "
        "counted."
    )


class is_orphan_supported_by_guardian(_Fact):
    value_type = bool
    label = "Orphan supported by a guardian"


class education_level(_Fact):
    value_type = Enum
    possible_values = EducationLevel
    default_value = EducationLevel.unknown
    label = "Course being studied, or applied for, this academic year"


class studies_abroad(_Fact):
    value_type = bool
    label = "The course is at an institution outside India"


class institution_recognised(_Fact):
    value_type = bool
    label = "School or institution is government-run or government-recognised"


class institution_eligible_for_fellowship(_Fact):
    value_type = bool
    label = (
        "University is UGC 2(f)/12(B), a UGC-funded deemed university, government-funded, "
        "or an Institute of National Importance"
    )


class admitted_to_top_class_institute(_Fact):
    value_type = bool
    label = "Admitted to an institute on the Top Class list, for a listed course"


class admitted_via_management_quota(_Fact):
    value_type = bool
    label = "Admitted through a management quota at a private institute"


class repeating_stage_in_other_subject(_Fact):
    value_type = bool
    label = (
        "Studying again at a level already passed, in a different subject (e.g. B.Com after B.A.)"
    )


class bachelors_marks_percent(_Fact):
    value_type = float
    label = "Percentage in Bachelor's degree"


class masters_marks_percent(_Fact):
    value_type = float
    label = "Percentage in Master's degree"


class net_jrf_qualified(_Fact):
    value_type = bool
    label = "Qualified UGC NET or Joint CSIR-UGC NET"


class has_overseas_admission_offer(_Fact):
    value_type = bool
    label = "Has an offer of admission from a university abroad"


class overseas_admission_in_qs_top_1000(_Fact):
    value_type = bool
    label = "That university is in the QS World University Rankings top 1,000"


class sibling_received_nos(_Fact):
    value_type = bool
    label = "A brother or sister has already received the National Overseas Scholarship"


class previously_received_nos(_Fact):
    value_type = bool
    label = "Has already received the National Overseas Scholarship before"


class current_mota_award(_Fact):
    value_type = Enum
    possible_values = MotaAward
    default_value = MotaAward.none
    label = "Ministry of Tribal Affairs scholarship currently held"


class holds_other_scholarship(_Fact):
    value_type = bool
    label = "Currently receives any other scholarship, fellowship or stipend"


class has_aadhaar_seeded_bank_account(_Fact):
    value_type = bool
    label = "Has a bank account in a scheduled bank, linked with Aadhaar and mobile number"


class gender(_Fact):
    value_type = Enum
    possible_values = Gender
    default_value = Gender.unknown
    label = "Gender"


class studies_by_distance(_Fact):
    value_type = bool
    label = "Studying by correspondence or distance learning"


class class_12_top_20_percent(_Fact):
    value_type = bool
    label = "Above the 80th percentile of Class XII passes in their stream and board"


class aicte_technical_first_year(_Fact):
    value_type = bool
    label = (
        "In the first year of a technical degree at an AICTE-approved institution, or the "
        "second year by lateral entry"
    )


class joined_within_two_years_of_class_12(_Fact):
    value_type = bool
    label = "Joined the degree course within two years of passing Class XII"


class selected_in_nmms_exam(_Fact):
    value_type = bool
    label = "Selected in the National Means-cum-Merit Scholarship exam at Class VIII"


class school_government_aided_or_local_body(_Fact):
    value_type = bool
    label = (
        "School is a government, government-aided or local body school (not a Kendriya "
        "Vidyalaya, Navodaya, residential or private school)"
    )
