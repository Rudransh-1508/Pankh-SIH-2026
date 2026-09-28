from datetime import date

from app.academic_year import current_academic_year, label


def test_upcoming_session_from_april():
    assert current_academic_year(date(2026, 3, 31)) == 2025
    assert current_academic_year(date(2026, 4, 1)) == 2026
    assert current_academic_year(date(2026, 12, 31)) == 2026


def test_label():
    assert label(2026) == "2026-27"
    assert label(2099) == "2099-00"
