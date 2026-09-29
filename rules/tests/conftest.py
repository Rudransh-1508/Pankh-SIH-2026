import pytest


@pytest.fixture
def base_facts() -> dict:
    """Facts shared by every eligible profile: an ST student with no other award."""
    return {
        "is_scheduled_tribe": True,
        "studies_abroad": False,
        "current_mota_award": "none",
        "holds_other_scholarship": False,
    }


_PROFILES = {
    "pre_matric": {
        "education_level": "class_9",
        "institution_recognised": True,
        "family_income": 180000,
        "has_aadhaar_seeded_bank_account": True,
    },
    "post_matric": {
        "education_level": "undergraduate",
        "institution_recognised": True,
        "family_income": 250000,
        "repeating_stage_in_other_subject": False,
        "admitted_to_top_class_institute": False,
    },
    "top_class": {
        "education_level": "undergraduate",
        "admitted_to_top_class_institute": True,
        "admitted_via_management_quota": False,
        "family_income": 540000,
    },
    "nfst": {
        "education_level": "phd",
        "masters_marks_percent": 61.5,
        "date_of_birth": "1998-03-14",
        "institution_eligible_for_fellowship": True,
        "net_jrf_qualified": True,
    },
    "csss": {
        "education_level": "undergraduate",
        "class_12_top_20_percent": True,
        "studies_by_distance": False,
        "institution_recognised": True,
        "family_income": 400000,
    },
    "pragati": {
        "gender": "female",
        "education_level": "undergraduate",
        "aicte_technical_first_year": True,
        "family_income": 700000,
        "joined_within_two_years_of_class_12": True,
    },
    "nmmss": {
        "education_level": "class_10",
        "selected_in_nmms_exam": True,
        "school_government_aided_or_local_body": True,
        "family_income": 300000,
    },
    "nos": {
        "education_level": "postgraduate",
        "studies_abroad": True,
        "has_overseas_admission_offer": True,
        "bachelors_marks_percent": 72,
        "date_of_birth": "2001-11-02",
        "family_income": 400000,
        "sibling_received_nos": False,
        "previously_received_nos": False,
    },
}


@pytest.fixture
def profiles(base_facts) -> dict[str, dict]:
    """A fully eligible Student per Scheme, as described by that Scheme's Guidelines."""
    return {scheme_id: base_facts | facts for scheme_id, facts in _PROFILES.items()}
