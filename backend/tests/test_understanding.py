import pytest

from app.jago.understanding import classify, parse_answer


@pytest.mark.parametrize(
    ("fact", "text", "value"),
    [
        ("is_scheduled_tribe", "haan", True),
        ("is_scheduled_tribe", "हाँ", True),
        ("is_scheduled_tribe", "Nahi", False),
        ("holds_other_scholarship", "no, none", False),
        ("family_income", "2.5 lakh", 250000),
        ("family_income", "ढाई लाख", 250000),
        ("family_income", "1 lakh 20 thousand", 120000),
        ("family_income", "1,80,000", 180000),
        ("family_income", "साढ़े 3 लाख", 350000),
        ("masters_marks_percent", "58.5%", 58.5),
        ("date_of_birth", "14/03/2008", "2008-03-14"),
        ("education_level", "BA", "undergraduate"),
        ("education_level", "class 10", "class_10"),
        ("education_level", "12th", "class_12"),
        ("education_level", "कक्षा 9", "class_9"),
        ("education_level", "Ph.D", "phd"),
        ("current_mota_award", "nahi", "none"),
    ],
)
def test_understands_answers(fact, text, value):
    assert parse_answer(fact, text) == value


@pytest.mark.parametrize(
    ("fact", "text"),
    [
        ("is_scheduled_tribe", "what is this?"),
        ("masters_marks_percent", "150"),
        ("education_level", "cricket"),
    ],
)
def test_ignores_what_is_not_an_answer(fact, text):
    assert parse_answer(fact, text) is None


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("Which scholarships can I get?", "eligibility"),
        ("मुझे कौन-सी छात्रवृत्ति मिल सकती है?", "eligibility"),
        ("Where is my application?", "applications"),
        ("status of my post matric application", "applications"),
        ("mera paisa kab aayega", "payments"),
        ("क्या मेरा पैसा आया?", "payments"),
        ("any problem with my documents", "documents"),
        ("tell me about top class", "scheme:top_class"),
        ("namaste", "greeting"),
        ("what's the weather", "unknown"),
    ],
)
def test_recognises_what_students_ask(text, intent):
    assert classify(text) == intent


def test_renewal_questions_are_about_renewal_even_when_they_mention_an_application():
    from app.jago.understanding import classify

    assert classify("renewal application for next year") == "renewal"
    assert classify("अगले साल नवीनीकरण") == "renewal"


def test_what_if_questions_go_to_the_scheme_path():
    from app.jago.understanding import classify

    assert classify("What if I get into an IIT?") == "path:top_class"
    assert classify("agar main NET pass karun") == "path:nfst"
    assert classify("अगर मैं विदेश में पढ़ूँ तो?") == "path:nos"
    assert classify("what is my plan for the future") == "path"
    # Naming a Scheme without asking about the future is still about that Scheme.
    assert classify("tell me about top class") == "scheme:top_class"


def test_plural_words_are_understood():
    from app.jago.understanding import classify

    assert classify("Hello, where are my applications?") == "applications"
    assert classify("any problems with my documents") == "documents"
    assert classify("have the payments come") == "payments"
