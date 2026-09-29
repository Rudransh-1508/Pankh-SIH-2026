"""Reading the fields a Fact needs from the text of a photographed Document.

The phone recognises the text; this module only matches patterns in it, in English and Hindi, so
no Document ever reaches a language model. It keeps the few fields a check needs and drops the
rest of the text.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Kind(StrEnum):
    CASTE_CERTIFICATE = "caste_certificate"
    INCOME_CERTIFICATE = "income_certificate"
    BACHELORS_MARKSHEET = "bachelors_marksheet"
    MASTERS_MARKSHEET = "masters_marksheet"


# The Fact each kind of Document proves.
FACT_FOR_KIND: dict[Kind, str] = {
    Kind.CASTE_CERTIFICATE: "is_scheduled_tribe",
    Kind.INCOME_CERTIFICATE: "family_income",
    Kind.BACHELORS_MARKSHEET: "bachelors_marks_percent",
    Kind.MASTERS_MARKSHEET: "masters_marks_percent",
}

KIND_NAMES: dict[Kind, str] = {
    Kind.CASTE_CERTIFICATE: "caste certificate",
    Kind.INCOME_CERTIFICATE: "income certificate",
    Kind.BACHELORS_MARKSHEET: "Bachelor's marksheet",
    Kind.MASTERS_MARKSHEET: "Master's marksheet",
}

# State names as certificates print them, with the codes state e-District portals use.
STATES: dict[str, tuple[str, ...]] = {
    "AP": ("Andhra Pradesh", "आंध्र प्रदेश"),
    "AR": ("Arunachal Pradesh", "अरुणाचल प्रदेश"),
    "AS": ("Assam", "असम"),
    "BR": ("Bihar", "बिहार"),
    "CG": ("Chhattisgarh", "छत्तीसगढ़", "छत्तीसगढ"),
    "GA": ("Goa", "गोवा"),
    "GJ": ("Gujarat", "गुजरात"),
    "HR": ("Haryana", "हरियाणा"),
    "HP": ("Himachal Pradesh", "हिमाचल प्रदेश"),
    "JH": ("Jharkhand", "झारखण्ड", "झारखंड"),
    "KA": ("Karnataka", "कर्नाटक"),
    "KL": ("Kerala", "केरल"),
    "MP": ("Madhya Pradesh", "मध्य प्रदेश", "मध्यप्रदेश"),
    "MH": ("Maharashtra", "महाराष्ट्र"),
    "MN": ("Manipur", "मणिपुर"),
    "ML": ("Meghalaya", "मेघालय"),
    "MZ": ("Mizoram", "मिज़ोरम", "मिजोरम"),
    "NL": ("Nagaland", "नागालैंड"),
    "OD": ("Odisha", "Orissa", "ओडिशा", "उड़ीसा"),
    "RJ": ("Rajasthan", "राजस्थान"),
    "SK": ("Sikkim", "सिक्किम"),
    "TN": ("Tamil Nadu", "तमिलनाडु"),
    "TS": ("Telangana", "तेलंगाना"),
    "TR": ("Tripura", "त्रिपुरा"),
    "UK": ("Uttarakhand", "उत्तराखण्ड", "उत्तराखंड"),
    "UP": ("Uttar Pradesh", "उत्तर प्रदेश"),
    "WB": ("West Bengal", "पश्चिम बंगाल"),
    "JK": ("Jammu and Kashmir", "जम्मू और कश्मीर"),
    "LA": ("Ladakh", "लद्दाख"),
    "AN": ("Andaman and Nicobar", "अंडमान और निकोबार"),
    "DN": ("Dadra and Nagar Haveli", "दादरा और नगर हवेली"),
    "LD": ("Lakshadweep", "लक्षद्वीप"),
}

_STATE_NAMES = {name: code for code, names in STATES.items() for name in names}


def state_code(name: str | None) -> str | None:
    """The e-District code for a state name, as DigiLocker or a certificate writes it."""
    if not name:
        return None
    wanted = name.strip().casefold()
    return next((code for n, code in _STATE_NAMES.items() if n.casefold() == wanted), None)


@dataclass(frozen=True)
class Reading:
    kind: Kind
    facts: dict[str, Any] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)
    """What was read, for the Student and the Reviewer to see."""
    problems: list[str] = field(default_factory=list)
    """Why the Fact could not be read, in words the Student can act on."""

    @property
    def fact(self) -> str:
        return FACT_FOR_KIND[self.kind]

    @property
    def readable(self) -> bool:
        return self.fact in self.facts


_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_FLAGS = re.IGNORECASE


def normalise(text: str) -> str:
    text = text.translate(_DEVANAGARI_DIGITS).replace("‌", "").replace("‍", "")
    return re.sub(r"\s+", " ", text).strip()


def _search(patterns: tuple[str, ...], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        if match := re.search(pattern, text, _FLAGS):
            return match
    return None


_NUMBER = (
    r"(?:certificate|cert)\.?\s*(?:no|number|num)\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})",
    r"(?:प्रमाण\s*-?\s*पत्र|प्रमाणपत्र)\s*(?:संख्या|क्रमांक|सं\.)\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-]{4,})",
)
_HONORIFICS_EN = r"(?:(?:shri|sri|smt|kumari|kum|km|sushri|mrs|mr|miss|ms)\b\.?\s*/?\s*)*"
_HONORIFICS_HI = r"(?:(?:श्रीमती|सुश्री|श्री|कुमारी|कु\.)\.?\s*/?\s*)*"
_NAME = (
    r"certify that\s+" + _HONORIFICS_EN + r"([A-Za-z][A-Za-z .]+?)\s*"
    r"(?:,|\b(?:son|daughter|wife|s/o|d/o|w/o|of|resident)\b)",
    r"प्रमाणित किया जाता है कि\s+" + _HONORIFICS_HI + r"([ऀ-ॿ][ऀ-ॿ .]+?)\s*"
    r"(?:,|पिता|पुत्र|पुत्री|पति|आत्मज|आत्मजा|निवासी)",
    r"(?:name of (?:the )?(?:candidate|student|applicant)|candidate'?s name|student'?s name|"
    r"\bname)\s*[:\-]\s*" + _HONORIFICS_EN + r"([A-Za-z][A-Za-z .]+?)\s*"
    r"(?=\b(?:father|mother|roll|enrol|registration|s/o|d/o|w/o|date|dob|gender|sex|address|"
    r"class|course|programme)\b|[,:]|$)",
    r"(?:नाम|आवेदक का नाम|छात्र का नाम)\s*[:\-]\s*" + _HONORIFICS_HI + r"([ऀ-ॿ][ऀ-ॿ .]+?)"
    r"\s*(?=पिता|माता|पति|अनुक्रमांक|जन्म|पता|[,:]|$)",
)


def _number(text: str) -> str | None:
    match = _search(_NUMBER, text)
    return match.group(1).upper().rstrip("/-") if match else None


def _holder(text: str) -> str | None:
    match = _search(_NAME, text)
    if not match:
        return None
    name = re.sub(r"\s+", " ", match.group(1)).strip(" .")
    return name.title() if name.isascii() else name


_STATE_PATTERNS = [
    (re.compile(rf"\b{re.escape(name)}\b" if name.isascii() else re.escape(name), _FLAGS), code)
    for name, code in _STATE_NAMES.items()
]


def _state(text: str) -> str | None:
    # A certificate names its issuing government first; take the earliest state mentioned.
    found = [(m.start(), code) for pattern, code in _STATE_PATTERNS if (m := pattern.search(text))]
    return min(found)[1] if found else None


_NOT_PLACE = {"of", "in", "the", "state", "and", "is", "has", "tehsil", "block", "pin", "police"}


def _district(text: str) -> str | None:
    match = re.search(r"(?:district|जिला|ज़िला)\s*[:\-]?\s*((?:\S+\s*){1,2})", text, _FLAGS)
    if not match:
        return None
    words = []
    for raw in match.group(1).split():
        word = raw.strip(".,;:\u0964")
        # str.isalpha() is False for Devanagari vowel signs, so match the script instead.
        if word.casefold() in _NOT_PLACE or not re.fullmatch(r"[A-Za-z\u0900-\u0963]+", word):
            break
        words.append(word)
        if raw != word:  # punctuation ends the name
            break
    if not words:
        return None
    name = " ".join(words)
    return name.title() if name.isascii() else name


def _common(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if number := _number(text):
        fields["certificate_number"] = number
    if holder := _holder(text):
        fields["holder_name"] = holder
    if state := _state(text):
        fields["state"] = STATES[state][0]
    if district := _district(text):
        fields["district"] = district
    return fields


def _caste(text: str) -> Reading:
    fields = _common(text)
    tribe = re.search(r"scheduled\s+tribes?|अनुसूचित\s+जन\s*जाति", text, _FLAGS)
    other = re.search(
        r"scheduled\s+castes?|other\s+backward|अनुसूचित\s+जाति|अन्य\s+पिछड़ा", text, _FLAGS
    )
    if tribe:
        fields["category"] = "ST"
        return Reading(Kind.CASTE_CERTIFICATE, {"is_scheduled_tribe": True}, fields)
    if other:
        return Reading(
            Kind.CASTE_CERTIFICATE,
            fields=fields,
            problems=[
                "This certificate does not say Scheduled Tribe. Ministry of Tribal Affairs "
                "scholarships need an ST certificate from your tehsil or e-District office."
            ],
        )
    return Reading(
        Kind.CASTE_CERTIFICATE,
        fields=fields,
        problems=["We could not find the words Scheduled Tribe on this certificate."],
    )


_AMOUNT = r"(?:rs\.?|₹|inr|रु\.?|रुपये|रूपये)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)"
_INCOME_LABEL = r"annual\s+income|income\s+from\s+all\s+sources|total\s+income|वार्षिक\s+आय|कुल\s+आय"


def _income_amount(text: str) -> float | None:
    for label in re.finditer(_INCOME_LABEL, text, _FLAGS):
        window = text[label.end() : label.end() + 120]
        if match := re.search(_AMOUNT, window, _FLAGS):
            return float(match.group(1).replace(",", ""))
        # Without a currency sign, take the first number that is not a year or year range.
        for match in re.finditer(
            r"(?<![\d/-])([0-9][0-9,]{2,}(?:\.[0-9]{1,2})?)(?![\d/-])", window
        ):
            digits = match.group(1).replace(",", "")
            if not re.fullmatch(r"(?:19|20)\d\d", digits):
                return float(digits)
    return None


def _financial_year(text: str) -> str | None:
    match = _search(
        (
            r"(?:financial\s+year|f\.?\s*y\.?|वित्तीय\s+वर्ष)\s*[:\-]?\s*(20\d\d)\s*[-\u2013/]\s*(?:20)?(\d\d)\b",
            r"\b(20\d\d)\s*[-\u2013]\s*(?:20)?(\d\d)\b",
        ),
        text,
    )
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    return f"{start}-{end:02d}" if (start + 1) % 100 == end else None


def _income(text: str) -> Reading:
    fields = _common(text)
    amount = _income_amount(text)
    if year := _financial_year(text):
        fields["financial_year"] = year
    if amount is None:
        return Reading(
            Kind.INCOME_CERTIFICATE,
            fields=fields,
            problems=["We could not find the annual income on this certificate."],
        )
    fields["annual_income"] = amount
    return Reading(Kind.INCOME_CERTIFICATE, {"family_income": amount}, fields)


def _percent(text: str) -> tuple[float | None, str | None]:
    match = _search(
        (
            r"(?:percentage|aggregate|overall|प्रतिशत)\s*(?:of\s+marks)?\s*(?:obtained)?\s*[:\-]?\s*"
            r"([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*%?",
            r"\b([0-9]{1,3}\.[0-9]{1,2})\s*%",
        ),
        text,
    )
    if match and 0 < float(match.group(1)) <= 100:
        return float(match.group(1)), None
    total = _search(
        (
            r"(?:grand\s+total|total\s+marks(?:\s+obtained)?|marks\s+obtained|कुल\s+(?:प्राप्तांक|योग))"
            r"\s*[:\-]?\s*([0-9]{2,4})\s*(?:/|out\s+of|में\s+से)\s*([0-9]{2,4})",
        ),
        text,
    )
    if total and 0 < int(total.group(1)) <= int(total.group(2)):
        return round(100 * int(total.group(1)) / int(total.group(2)), 2), None
    if re.search(r"\b[cs]gpa\b", text, _FLAGS):
        return None, (
            "This marksheet gives a CGPA, not a percentage. Ask your university for its "
            "percentage conversion certificate and photograph that too."
        )
    return None, None


def _marksheet(kind: Kind, text: str) -> Reading:
    fields = _common(text)
    fields.pop("certificate_number", None)
    percent, problem = _percent(text)
    if percent is None:
        return Reading(
            kind,
            fields=fields,
            problems=[problem or "We could not find the percentage on this marksheet."],
        )
    fields["percent"] = percent
    return Reading(kind, {FACT_FOR_KIND[kind]: percent}, fields)


def read_document(kind: Kind, text: str) -> Reading:
    text = normalise(text)
    if len(text) < 20:
        return Reading(kind, problems=["We could not read any text in this photo."])
    match kind:
        case Kind.CASTE_CERTIFICATE:
            return _caste(text)
        case Kind.INCOME_CERTIFICATE:
            return _income(text)
        case Kind.BACHELORS_MARKSHEET | Kind.MASTERS_MARKSHEET:
            return _marksheet(kind, text)
