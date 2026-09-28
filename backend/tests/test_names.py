import pytest

from app.verification.names import MATCH_THRESHOLD, match_names, name_key


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Phulmani Hansda", "Fulmani Hansdah"),
        ("Rinki Tirkey", "Tirkey Rinki"),
        ("Km. Sunita Murmu", "Sunita Murmu"),
        ("सुनीता मुर्मू", "Sunita Murmu"),
        ("Pooja Kerketta", "Puja Kerketa"),
        ("रमेश उइके", "Ramesh Uikey"),
        ("Dinesh Kumar Minz", "Dinesh Minj"),
        ("Jyoti Basumatary", "Jyothi Basumatari"),
    ],
)
def test_same_person_written_differently(left, right):
    assert match_names(left, right).is_match, match_names(left, right)


def test_missing_surname_needs_review():
    result = match_names("Sunita", "Sunita Murmu")
    assert 0.6 < result.score < MATCH_THRESHOLD
    assert not result.is_match


@pytest.mark.parametrize(
    ("left", "right"),
    [("Rahul Soren", "Sunita Murmu"), ("Anita Tudu", "Anil Tudu"), ("Birsa Munda", "Budhu Munda")],
)
def test_different_people(left, right):
    assert not match_names(left, right).is_match, match_names(left, right)


def test_keys_ignore_honorifics_and_script():
    assert name_key("Shri Ramesh") == name_key("रमेश")
    assert match_names("", "Sunita").score == 0
