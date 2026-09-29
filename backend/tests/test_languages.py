"""Every text table has every language, with the same placeholders as English, so no language
falls over at runtime on a missing key or an unfilled {placeholder}."""

import string

import pytest

from app.jago.texts import TEXT, WHO
from app.jago.understanding import classify, parse_boolean
from app.languages import LANGUAGES, NAMES, SPEECH
from app.letters.texts import CASTE_CERTIFICATE, CLOSING, LETTERS
from app.outreach.messages import _FAMILY, _OR, _SCHOOL
from app.outreach.router import _CHECKS, _LIST_TEXT
from pankh_rules.questions import LANGUAGES as QUESTION_LANGUAGES


def placeholders(text: str) -> set[str]:
    return {field for _, field, _, _ in string.Formatter().parse(text) if field}


def test_the_rules_ask_questions_in_the_same_languages():
    assert set(QUESTION_LANGUAGES) == set(LANGUAGES)


def test_every_language_has_a_name_and_a_voice():
    assert set(NAMES) == set(SPEECH) == set(LANGUAGES)


@pytest.mark.parametrize("language", LANGUAGES)
def test_jago_speaks_every_language(language):
    assert set(TEXT[language]) == set(TEXT["en"])
    assert set(WHO[language]) == set(WHO["en"])
    for key, english in TEXT["en"].items():
        if isinstance(english, str):
            assert placeholders(TEXT[language][key]) == placeholders(english), key


@pytest.mark.parametrize("language", LANGUAGES)
def test_jago_understands_its_own_suggestions(language):
    """Without a model, the tappable suggestions must still reach the right answer."""
    text = TEXT[language]
    assert [classify(s) for s in text["suggest"]] == [
        "eligibility",
        "applications",
        "payments",
        "documents",
    ]
    assert [classify(s) for s in text["path_suggest"]] == [
        "path:top_class",
        "path:nfst",
        "path:nos",
    ]
    assert [parse_boolean(word) for word in text["yes_no"]] == [True, False]


@pytest.mark.parametrize("language", LANGUAGES)
def test_letters_and_outreach_are_in_every_language(language):
    for kind, versions in LETTERS.items():
        for key, english in versions["en"].items():
            assert placeholders(versions[language][key]) == placeholders(english), (kind, key)
    assert placeholders(CLOSING[language]) == placeholders(CLOSING["en"])
    assert language in CASTE_CERTIFICATE and language in _OR
    assert placeholders(_SCHOOL[language]) == placeholders(_SCHOOL["en"])
    assert placeholders(_FAMILY[language]) == placeholders(_FAMILY["en"])
    assert set(_LIST_TEXT[language]) == set(_LIST_TEXT["en"])
    assert all(language in labels for labels in _CHECKS.values())
