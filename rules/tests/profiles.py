"""Fully eligible Students, one per Scheme, as described by each Scheme's Guidelines."""

PROFILES = {
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
