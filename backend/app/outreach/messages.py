"""The words of outreach messages, in each language. Fixed templates, never generated.

Every message names the ministry, says applying is free, and (to families) warns that nobody
will ask for money or a code, because scholarship fraud targets exactly these families.
"""

from typing import Literal

Language = Literal["en", "hi"]

_SCHOOL = {
    "en": (
        "Pankh, Ministry of Tribal Affairs: {count} ST students at {school} may qualify for "
        "{schemes} but have not applied. The list, with what each can apply for: {link} "
        "(valid for 30 days)."
    ),
    "hi": (
        "पंख, जनजातीय कार्य मंत्रालय: {school} के {count} अनुसूचित जनजाति विद्यार्थी {schemes} "
        "के पात्र हो सकते हैं, पर उन्होंने आवेदन नहीं किया है। सूची और हर विद्यार्थी की योजना: "
        "{link} (30 दिन मान्य)।"
    ),
}

_FAMILY = {
    "en": (
        "Pankh, Ministry of Tribal Affairs: {name} may qualify for the {schemes} scholarship. "
        "Applying is free: ask at your school or use the Pankh app. Nobody will ask you for "
        "money or an OTP."
    ),
    "hi": (
        "पंख, जनजातीय कार्य मंत्रालय: {name} को {schemes} छात्रवृत्ति मिल सकती है। आवेदन "
        "निःशुल्क है: अपने स्कूल में पूछें या पंख ऐप का उपयोग करें। कोई भी आपसे पैसे या OTP "
        "नहीं माँगेगा।"
    ),
}

_OR = {"en": " or ", "hi": " या "}


def _schemes(names: list[str], language: Language) -> str:
    unique = list(dict.fromkeys(names))
    if len(unique) <= 1:
        return "".join(unique)
    return ", ".join(unique[:-1]) + _OR[language] + unique[-1]


def school_message(
    language: Language, school: str, count: int, schemes: list[str], link: str
) -> str:
    return _SCHOOL[language].format(
        school=school, count=count, schemes=_schemes(schemes, language), link=link
    )


def family_message(language: Language, name: str, schemes: list[str]) -> str:
    first_name = name.split()[0] if name.split() else name
    return _FAMILY[language].format(name=first_name, schemes=_schemes(schemes, language))
