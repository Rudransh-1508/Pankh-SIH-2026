from pankh_rules import plan_path

STUDENT = {
    "is_scheduled_tribe": True,
    "education_level": "class_11",
    "studies_abroad": False,
    "institution_recognised": True,
    "family_income": 180000,
    "date_of_birth": "2010-05-04",
    "repeating_stage_in_other_subject": False,
    "admitted_to_top_class_institute": False,
    "current_mota_award": "none",
    "holds_other_scholarship": False,
}


def test_path_runs_from_the_current_stage_to_doctoral_study():
    stages = plan_path(STUDENT, 2026)
    assert [s.level for s in stages] == [
        "class_11",
        "class_12",
        "undergraduate",
        "postgraduate",
        "phd",
    ]
    assert stages[0].label == "2026-27"
    assert stages[2].label == "2028-29 to 2030-31"


def test_one_scheme_is_recommended_at_each_stage():
    stages = plan_path(STUDENT, 2026)
    assert all(stage.recommended.scheme_id == "post_matric" for stage in stages)
    assert stages[0].recommended.value.yearly_inr is None  # fees depend on the course
    assert stages[0].recommended.value.citation.source_id == "post-matric-regulations"


def test_better_schemes_appear_as_opportunities_with_what_to_do():
    stages = {s.level: s for s in plan_path(STUDENT, 2026)}
    top_class = next(o for o in stages["undergraduate"].opportunities if o.scheme_id == "top_class")
    assert "Top Class institutes" in top_class.condition
    phd = {o.scheme_id for o in stages["phd"].opportunities}
    assert "nfst" in phd


def test_age_limits_close_opportunities_later_in_life():
    older = STUDENT | {"date_of_birth": "1990-01-01", "education_level": "postgraduate"}
    stages = {s.level: s for s in plan_path(older, 2026)}
    assert "nfst" not in {o.scheme_id for o in stages["phd"].opportunities}  # over 36 by then


def test_no_path_without_a_course():
    assert plan_path({"is_scheduled_tribe": True}, 2026) == []
