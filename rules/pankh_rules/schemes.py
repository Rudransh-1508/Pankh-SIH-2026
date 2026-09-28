"""The five MoTA Schemes: their Rules, benefits and where each comes from.

Rule texts are templates. Placeholders are filled from the Student's Facts (formatted for
display) and from the parameter values named in `values`, as in force for the academic year.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pankh_rules.citations import Citation, cite

FactsView = Mapping[str, Any]


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    citation: Citation
    requires: tuple[str, ...] | Callable[[FactsView], tuple[str, ...]]
    fail_reason: str
    remedy: str | None = None
    waived_by: str | None = None
    values: Mapping[str, str | Callable[[FactsView], str]] = field(default_factory=dict)

    @property
    def variable(self) -> str:
        return self.id.replace(".", "__")

    def required_facts(self, facts: FactsView) -> tuple[str, ...]:
        return self.requires(facts) if callable(self.requires) else self.requires

    def parameter_paths(self, facts: FactsView) -> dict[str, str]:
        return {name: path(facts) if callable(path) else path for name, path in self.values.items()}


@dataclass(frozen=True)
class Benefit:
    text: str
    citation: Citation


@dataclass(frozen=True)
class Scheme:
    id: str
    name: str
    short_name: str
    summary: str
    system_of_record: str
    apply_url: str
    application_window: str | None
    benefits: tuple[Benefit, ...]
    rules: tuple[Rule, ...]


# Shared Rule builders. Each Scheme cites its own Guideline for the same kind of condition.


def _scheduled_tribe(scheme: str, citation: Citation) -> Rule:
    return Rule(
        id=f"{scheme}.scheduled_tribe",
        title="Belongs to a Scheduled Tribe",
        citation=citation,
        requires=("is_scheduled_tribe",),
        fail_reason="This scheme is only for students from a Scheduled Tribe notified for "
        "their domicile state.",
    )


def _income(scheme: str, citation: Citation, orphan_waiver: bool) -> Rule:
    return Rule(
        id=f"{scheme}.income_within_ceiling",
        title="Family income is at most {ceiling} a year",
        citation=citation,
        requires=("family_income",),
        waived_by="is_orphan_supported_by_guardian" if orphan_waiver else None,
        values={"ceiling": f"{scheme}.income_ceiling"},
        fail_reason="Your family income of {family_income} is above the limit of {ceiling}.",
        remedy="Only the income of your parents (and spouse, if married) counts, not siblings "
        "or other relatives. If your income certificate includes other earners, or your "
        "family's income has fallen, a fresh certificate from the competent authority may "
        "bring you under {ceiling}.",
    )


def _no_other_mota_award(scheme: str, citation: Citation) -> Rule:
    return Rule(
        id=f"{scheme}.no_other_mota_award",
        title="Not holding another Ministry of Tribal Affairs scholarship",
        citation=citation,
        requires=("current_mota_award",),
        fail_reason="You already hold the {current_mota_award}. A student can hold only one "
        "Ministry of Tribal Affairs scholarship at a time.",
        remedy="You can switch if this scheme suits you better: give up the current award "
        "through your institution before accepting this one.",
    )


def _no_other_scholarship(scheme: str, citation: Citation) -> Rule:
    return Rule(
        id=f"{scheme}.no_other_scholarship",
        title="Not receiving any other scholarship or stipend",
        citation=citation,
        requires=("holds_other_scholarship",),
        fail_reason="You already receive another scholarship, fellowship or stipend.",
        remedy="You may choose whichever scholarship is more beneficial. Tell your institution "
        "which one you keep; this one is paid only after the other stops.",
    )


PRE_MATRIC = Scheme(
    id="pre_matric",
    name="Pre-Matric Scholarship for ST Students",
    short_name="Pre-Matric",
    summary="Support for ST students in Classes IX and X so they can continue to secondary "
    "school and beyond.",
    system_of_record="National Scholarship Portal or your State scholarship portal",
    apply_url="https://scholarships.gov.in",
    application_window="Usually 1 April to 31 July; your State announces the exact dates.",
    benefits=(
        Benefit(
            "₹225 a month for day scholars, or ₹525 a month for hostellers, for 10 months",
            cite("pre-matric-guidelines-2022", 4, "para 3.4"),
        ),
        Benefit(
            "Books and ad hoc grant of ₹750 a year (day scholars) or ₹1,000 (hostellers)",
            cite("pre-matric-guidelines-2022", 4, "para 3.4"),
        ),
        Benefit(
            "Extra ₹600 a month (day scholars) or ₹800 a month (hostellers) for students with "
            "disabilities, including leprosy-cured students and those with sickle cell anaemia "
            "or thalassaemia",
            cite("pre-matric-guidelines-2022", 4, "para 3.4"),
        ),
    ),
    rules=(
        _scheduled_tribe("pre_matric", cite("pre-matric-guidelines-2022", 3, "para 3.2 (I)")),
        Rule(
            id="pre_matric.class_ix_or_x",
            title="Studying in Class IX or X in India",
            citation=cite("pre-matric-guidelines-2022", 3, "paras 3.1 and 3.2"),
            requires=("education_level", "studies_abroad"),
            fail_reason="This scheme covers only Classes IX and X in India.",
        ),
        Rule(
            id="pre_matric.recognised_school",
            title="School is government-run or government-recognised",
            citation=cite("pre-matric-guidelines-2022", 3, "para 3.2 (II)"),
            requires=("institution_recognised",),
            fail_reason="The school must be a government school or recognised by the "
            "government or a Central or State Board.",
            remedy="Check with your school whether it is recognised; ask for its U-DISE code.",
        ),
        _income(
            "pre_matric",
            cite("pre-matric-guidelines-2022", 3, "paras 3.2 (III) and 3.3"),
            orphan_waiver=True,
        ),
        Rule(
            id="pre_matric.aadhaar_seeded_bank_account",
            title="Has a bank account linked with Aadhaar and mobile number",
            citation=cite("pre-matric-guidelines-2022", 3, "para 3.2 (IV)"),
            requires=("has_aadhaar_seeded_bank_account",),
            fail_reason="The scholarship is paid directly into a bank account linked with "
            "Aadhaar and a mobile number.",
            remedy="Open an account at a scheduled bank or post office, and ask the bank to "
            "link it with your Aadhaar and mobile number.",
        ),
        _no_other_mota_award("pre_matric", cite("pre-matric-guidelines-2022", 3, "para 3.2 (V)")),
        _no_other_scholarship("pre_matric", cite("pre-matric-guidelines-2022", 3, "para 3.2 (V)")),
    ),
)


POST_MATRIC = Scheme(
    id="post_matric",
    name="Post-Matric Scholarship for ST Students",
    short_name="Post-Matric",
    summary="Support for ST students studying after Class X, from Class XI to doctoral "
    "research, at recognised institutions in India.",
    system_of_record="National Scholarship Portal or your State scholarship portal",
    apply_url="https://scholarships.gov.in",
    application_window="Set by your State each year.",
    benefits=(
        Benefit(
            "Monthly maintenance allowance, at rates that depend on your course group and "
            "whether you are a day scholar or hosteller",
            cite("post-matric-regulations", 9, "section V"),
        ),
        Benefit(
            "Reimbursement of compulsory non-refundable fees",
            cite("post-matric-regulations", 9, "section V"),
        ),
        Benefit(
            "Study tour and thesis typing or printing charges, and extra support for students "
            "with disabilities",
            cite("post-matric-regulations", 9, "section V"),
        ),
    ),
    rules=(
        _scheduled_tribe("post_matric", cite("post-matric-regulations", 6, "section III (iii)")),
        Rule(
            id="post_matric.post_matric_course_in_india",
            title="Studying a post-matric course (Class XI or above) in India",
            citation=cite("post-matric-regulations", 6, "section III (ii) and (iii)"),
            requires=("education_level", "studies_abroad"),
            fail_reason="This scheme covers courses after Class X, studied in India.",
        ),
        Rule(
            id="post_matric.recognised_institution",
            title="Institution is recognised",
            citation=cite("post-matric-regulations", 6, "section III (ii)"),
            requires=("institution_recognised",),
            fail_reason="The course must be at a recognised institution.",
            remedy="Check that your institution is recognised; ask for its AISHE code.",
        ),
        _income(
            "post_matric",
            cite("post-matric-regulations", 1, "letter of 23 May 2013, para 2"),
            orphan_waiver=False,
        ),
        Rule(
            id="post_matric.not_repeating_stage",
            title="Not repeating a level already passed, in another subject",
            citation=cite("post-matric-regulations", 7, "section III (iv)"),
            requires=("repeating_stage_in_other_subject",),
            fail_reason="Studying again at a level you have already passed, in a different "
            "subject (for example B.Com after B.A.), is not covered.",
        ),
        Rule(
            id="post_matric.not_at_top_class_institute",
            title="Not admitted to a Top Class institute",
            citation=cite("nfs-guidelines-2022", 18, "Part B para 2.3"),
            requires=("admitted_to_top_class_institute",),
            fail_reason="Students at Top Class institutes are covered by the Top Class "
            "Scholarship instead of Post-Matric.",
            remedy="Check your eligibility for the Top Class Scholarship, which pays more.",
        ),
        _no_other_mota_award(
            "post_matric", cite("post-matric-regulations", 8, "section III (xii)")
        ),
        _no_other_scholarship(
            "post_matric", cite("post-matric-regulations", 8, "section III (xii)")
        ),
    ),
)


TOP_CLASS = Scheme(
    id="top_class",
    name="National Scholarship for ST Students (Top Class)",
    short_name="Top Class",
    summary="Full support for ST students admitted to 265 notified premier institutes for "
    "graduate and postgraduate courses.",
    system_of_record="National Scholarship Portal",
    apply_url="https://scholarships.gov.in",
    application_window="Announced each year on the National Scholarship Portal.",
    benefits=(
        Benefit(
            "Full tuition, admission and other non-refundable fees (up to ₹2.5 lakh a year at "
            "private institutes)",
            cite("nfs-guidelines-2022", 19, "Part B para 2.5"),
        ),
        Benefit("Stipend of ₹3,000 a month", cite("nfs-guidelines-2022", 19, "Part B para 2.5")),
        Benefit(
            "Books and stationery, ₹5,000 a year",
            cite("nfs-guidelines-2022", 19, "Part B para 2.5"),
        ),
        Benefit(
            "One-time ₹45,000 for a computer and accessories",
            cite("nfs-guidelines-2022", 19, "Part B para 2.5"),
        ),
    ),
    rules=(
        _scheduled_tribe("top_class", cite("nfs-guidelines-2022", 17, "Part B para 2.1")),
        Rule(
            id="top_class.graduate_or_postgraduate_course",
            title="Studying a graduate or postgraduate course",
            citation=cite("nfs-guidelines-2022", 17, "Part B para 2.1"),
            requires=("education_level",),
            fail_reason="This scheme covers graduate and postgraduate courses only.",
        ),
        Rule(
            id="top_class.admitted_to_notified_institute",
            title="Admitted to a notified Top Class institute",
            citation=cite("nfs-guidelines-2022", 18, "Part B para 2.3"),
            requires=("admitted_to_top_class_institute",),
            fail_reason="Your institute or course is not on the ministry's list of 265 "
            "notified Top Class institutes.",
            remedy="If you are preparing for admission, the Top Class list shows which "
            "institutes and courses qualify.",
        ),
        Rule(
            id="top_class.not_management_quota",
            title="Not admitted through a management quota",
            citation=cite("nfs-guidelines-2022", 18, "Part B para 2.4"),
            requires=("admitted_via_management_quota",),
            fail_reason="Students admitted through a management quota at a private institute "
            "are not covered.",
        ),
        _income(
            "top_class", cite("nfs-guidelines-2022", 17, "Part B para 2.2"), orphan_waiver=True
        ),
        _no_other_mota_award("top_class", cite("nfs-guidelines-2022", 17, "Part B para 2.1")),
        _no_other_scholarship("top_class", cite("nfs-guidelines-2022", 17, "Part B para 2.1")),
    ),
)


NFST = Scheme(
    id="nfst",
    name="National Fellowship for ST Students (NFST)",
    short_name="NFST",
    summary="Fellowships for ST scholars pursuing M.Phil or Ph.D at eligible universities "
    "in India.",
    system_of_record="National Fellowship portal (fellowship.tribal.gov.in), with payments "
    "through Canara Bank",
    apply_url="https://fellowship.tribal.gov.in",
    application_window="Usually 1 July to 30 September.",
    benefits=(
        Benefit(
            "Fellowship of ₹37,000 a month for the first two years, then ₹42,000 a month",
            cite("nfst-rate-revision-2023", 1, "revised rates from 01.01.2023"),
        ),
        Benefit(
            "Annual contingency grant for a Ph.D: ₹20,500 (humanities and social sciences) or "
            "₹25,000 (science, engineering and technology)",
            cite("nfs-guidelines-2022", 7, "Part A para 2.6"),
        ),
        Benefit(
            "House rent allowance at UGC rates, and ₹2,000 a month escort allowance for "
            "scholars with disabilities",
            cite("nfs-guidelines-2022", 7, "Part A para 2.6"),
        ),
    ),
    rules=(
        _scheduled_tribe("nfst", cite("nfs-guidelines-2022", 4, "Part A para 2")),
        Rule(
            id="nfst.research_course_in_india",
            title="Pursuing a regular, full-time M.Phil or Ph.D in India",
            citation=cite("nfs-guidelines-2022", 5, "Part A paras 2.1 and 2.4"),
            requires=("education_level", "studies_abroad"),
            fail_reason="The fellowship is for M.Phil or Ph.D studies in India.",
        ),
        Rule(
            id="nfst.masters_marks",
            title="At least {minimum}% in your Master's degree",
            citation=cite("nfs-guidelines-2022", 5, "Part A para 2.1 (ii)"),
            requires=("masters_marks_percent",),
            values={"minimum": "nfst.min_masters_marks_percent"},
            fail_reason="Your Master's percentage of {masters_marks_percent} is below "
            "the required {minimum}%.",
            remedy="If your university grades in CGPA, use the university's official "
            "conversion formula; the converted percentage may meet {minimum}%.",
        ),
        Rule(
            id="nfst.age_limit",
            title="Aged {max_age} or under on 1 July",
            citation=cite("nfs-guidelines-2022", 5, "Part A para 2.3"),
            requires=("date_of_birth",),
            values={"max_age": "nfst.max_age"},
            fail_reason="You are {age_on_1_july} on 1 July, above the limit of {max_age}.",
        ),
        Rule(
            id="nfst.eligible_institution",
            title="University or institute is eligible for the fellowship",
            citation=cite("nfs-guidelines-2022", 5, "Part A para 2.4"),
            requires=("institution_eligible_for_fellowship",),
            fail_reason="The university must be UGC 2(f)/12(B), a UGC-funded deemed "
            "university, government-funded, or an Institute of National Importance.",
        ),
        Rule(
            id="nfst.net_qualified",
            title="Qualified UGC NET or Joint CSIR-UGC NET",
            citation=cite("nfst-selection-netjrf-2024", 1, "paras 2 and 3"),
            requires=("net_jrf_qualified",),
            fail_reason="From 2025-26, applicants must qualify UGC NET or Joint CSIR-UGC NET. "
            "Selection gives equal weight to NET marks and Master's marks.",
            remedy="Register for the next UGC NET or Joint CSIR-UGC NET examination.",
        ),
        _no_other_mota_award("nfst", cite("nfs-guidelines-2022", 8, "Part A para 2.6.1, Note 1")),
        _no_other_scholarship("nfst", cite("nfs-guidelines-2022", 8, "Part A para 2.6.1, Note 1")),
    ),
)


def _nos_marks_requirements(facts: FactsView) -> tuple[str, ...]:
    if facts.get("education_level") == "postgraduate":
        return ("education_level", "bachelors_marks_percent")
    return ("education_level", "masters_marks_percent")


def _nos_age_parameter(facts: FactsView) -> str:
    return {
        "postgraduate": "nos.max_age.masters",
        "phd": "nos.max_age.phd",
        "postdoc": "nos.max_age.postdoc",
    }.get(facts.get("education_level", ""), "nos.max_age.masters")


NOS = Scheme(
    id="nos",
    name="National Overseas Scholarship for ST Students (NOS)",
    short_name="NOS",
    summary="Scholarships for ST students pursuing a Master's or Ph.D at reputed universities "
    "abroad.",
    system_of_record="NOS Portal (overseas.tribal.gov.in)",
    apply_url="https://overseas.tribal.gov.in",
    application_window=None,
    benefits=(
        Benefit(
            "Annual maintenance allowance of US$15,400 (USA) or £9,900 (UK)",
            cite("nos-guidelines-2022", 5, "para 3.2"),
        ),
        Benefit(
            "Annual contingency and equipment allowance of US$1,532 (USA) or £1,116 (UK)",
            cite("nos-guidelines-2022", 5, "para 3.2"),
        ),
        Benefit(
            "Tuition and compulsory fees, visa fees and medical insurance at actual cost",
            cite("nos-guidelines-2022", 6, "para 3.2"),
        ),
        Benefit(
            "Economy air fare from India to the university and back",
            cite("nos-guidelines-2022", 6, "para 3.2"),
        ),
    ),
    rules=(
        _scheduled_tribe("nos", cite("nos-guidelines-2022", 3, "para 1")),
        Rule(
            id="nos.covered_course_abroad",
            title="Pursuing a covered postgraduate course abroad",
            citation=cite("nos-amendment-2026", 1, "para 2 (i), amending NOS guidelines para 2.1"),
            requires=("education_level", "studies_abroad"),
            fail_reason="The scholarship covers Master's and Ph.D courses abroad. Bachelor's "
            "courses are not covered, and post-doctoral research is not covered from 2026-27.",
        ),
        Rule(
            id="nos.admission_offer",
            title="Has an offer of admission from a university abroad",
            citation=cite("nos-guidelines-2022", 8, "para 4.3"),
            requires=("has_overseas_admission_offer",),
            fail_reason="You need an offer of admission from a foreign university to apply.",
            remedy="Selection gives first priority to offers from the top 1,000 universities "
            "in the QS World University Rankings.",
        ),
        Rule(
            id="nos.qualifying_marks",
            title="At least {minimum}% in your qualifying degree",
            citation=cite("nos-guidelines-2022", 3, "para 2.2 (i)"),
            requires=_nos_marks_requirements,
            waived_by="overseas_admission_in_qs_top_1000",
            values={"minimum": "nos.min_marks_percent"},
            fail_reason="You need at least {minimum}% in your qualifying degree (Bachelor's for "
            "a Master's course, Master's for a Ph.D).",
            remedy="The marks requirement does not apply if you have admission at a university "
            "in the QS World University Rankings top 1,000.",
        ),
        Rule(
            id="nos.age_limit",
            title="Aged {max_age} or under on 1 July",
            citation=cite("nos-guidelines-2022", 3, "para 2.2 (i)"),
            requires=("education_level", "date_of_birth"),
            values={"max_age": _nos_age_parameter},
            fail_reason="You are {age_on_1_july} on 1 July, above the limit of {max_age} for "
            "this level of course.",
        ),
        _income("nos", cite("nos-guidelines-2022", 4, "para 2.2 (iii)"), orphan_waiver=True),
        Rule(
            id="nos.one_child_per_family",
            title="No brother or sister has received this scholarship",
            citation=cite("nos-guidelines-2022", 4, "para 2.2 (ii)"),
            requires=("sibling_received_nos",),
            fail_reason="Only one child of the same parents can receive the National Overseas "
            "Scholarship.",
        ),
        Rule(
            id="nos.first_award",
            title="Has not received this scholarship before",
            citation=cite("nos-guidelines-2022", 4, "para 2.2 (ii)"),
            requires=("previously_received_nos",),
            fail_reason="The National Overseas Scholarship can be received only once.",
        ),
        _no_other_mota_award("nos", cite("nos-guidelines-2022", 7, "para 3.2, Note 2")),
        _no_other_scholarship("nos", cite("nos-guidelines-2022", 7, "para 3.2, Note 2")),
    ),
)


SCHEMES: dict[str, Scheme] = {
    scheme.id: scheme for scheme in (PRE_MATRIC, POST_MATRIC, TOP_CLASS, NFST, NOS)
}
