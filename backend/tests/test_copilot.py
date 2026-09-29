from app.review.copilot import Precedent, summarise, word_differences


def test_word_differences_explain_each_word():
    pairs = word_differences("Kumari Sunita Murmoo", "Sunita Murmu")
    notes = {(p.on_document, p.on_aadhaar): p.note for p in pairs}
    assert notes[("Kumari", None)] == "a title, which is ignored"
    assert notes[("Sunita", "Sunita")] == "same"
    assert notes[("Murmoo", "Murmu")] == "spelt differently, sounds the same"
    different = word_differences("Anita Tudu", "Anil Tudu")
    assert different[0].note.startswith("different word")
    missing = word_differences("Birsa", "Birsa Oraon")
    assert (missing[-1].on_aadhaar, missing[-1].note) == ("Oraon", "only on Aadhaar")


def test_a_name_case_summary_points_at_the_word_and_never_decides():
    summary = summarise(
        "name_mismatch",
        "is_scheduled_tribe",
        {"name_on_document": "Anita Tudu", "name_on_aadhaar": "Anil Tudu"},
        {"is_scheduled_tribe": {"value": True, "verified": False}},
        None,
        Precedent(confirmed=3, returned=1),
    )
    assert summary.headline == "The names do not clearly match"
    assert any(p.startswith("Differs: Anita / Anil: different word") for p in summary.points)
    assert "Similar cases in this state: 3 confirmed, 1 returned to the student." in summary.points
    text = " ".join(summary.points + summary.look_at).lower()
    assert "recommend" not in text and "should confirm" not in text


def test_swapped_day_and_month_are_spotted():
    summary = summarise(
        "value_conflict",
        "date_of_birth",
        {"given": "2005-03-11", "confirmed": "2005-11-03"},
        {},
        None,
        None,
    )
    assert "Day and month are swapped: a common data-entry slip." in summary.points
