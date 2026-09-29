"""Understanding what a Student means, in English, Hindi or a mix, without a language model.

This is what lets JAGO work with no model at all (offline, or where a model is too costly):
answers to its own questions ("haan", "ढाई लाख", "class 10", "BA") and the handful of things
Students most often ask.
"""

import re
import unicodedata
from datetime import date, datetime
from typing import Any

import pankh_rules

_YES = {
    "yes",
    "y",
    "yeah",
    "yep",
    "haan",
    "haa",
    "ha",
    "han",
    "hanji",
    "ji",
    "हाँ",
    "हां",
    "हा",
    "जी",
    "जीहाँ",
    "sahi",
    "correct",
    "है",
}
_NO = {"no", "n", "nope", "nahi", "nahin", "nai", "na", "नहीं", "नही", "ना", "none", "कोई", "koi"}

_HINDI_FRACTIONS = {"डेढ़": 1.5, "डेढ": 1.5, "dedh": 1.5, "ढाई": 2.5, "dhai": 2.5}
_MULTIPLIERS = {
    "lakh": 100_000,
    "lac": 100_000,
    "lakhs": 100_000,
    "लाख": 100_000,
    "thousand": 1_000,
    "hazar": 1_000,
    "hajar": 1_000,
    "हज़ार": 1_000,
    "हजार": 1_000,
    "k": 1_000,
    "crore": 10_000_000,
    "करोड़": 10_000_000,
}

# Ways Students name their course, mapped to education_level choices.
_COURSES = {
    "class_9": ("9", "9th", "ix", "ninth", "कक्षा 9", "नौवीं", "नवमी"),
    "class_10": ("10", "10th", "x", "tenth", "matric", "कक्षा 10", "दसवीं"),
    "class_11": ("11", "11th", "xi", "eleventh", "कक्षा 11", "ग्यारहवीं"),
    "class_12": ("12", "12th", "xii", "twelfth", "inter", "intermediate", "कक्षा 12", "बारहवीं"),
    "diploma": ("diploma", "iti", "polytechnic", "डिप्लोमा"),
    "undergraduate": (
        "ba",
        "bsc",
        "bcom",
        "btech",
        "be",
        "bba",
        "bca",
        "graduation",
        "bachelor",
        "bachelors",
        "ug",
        "degree",
        "स्नातक",
        "बीए",
    ),
    "postgraduate": (
        "ma",
        "msc",
        "mcom",
        "mtech",
        "mba",
        "mca",
        "master",
        "masters",
        "pg",
        "post graduation",
        "स्नातकोत्तर",
        "एमए",
    ),
    "mphil": ("mphil", "m.phil", "एमफिल"),
    "phd": ("phd", "ph.d", "doctorate", "पीएचडी"),
    "postdoc": ("postdoc", "post doc", "post-doctoral"),
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower().strip()
    return re.sub(r"[?!।,]+$", "", text).strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[\wऀ-ॿ.]+", _norm(text))


def parse_boolean(text: str) -> bool | None:
    words = set(_words(text)) | {_norm(text).replace(" ", "")}
    if words & _NO:
        return False
    if words & _YES:
        return True
    return None


def parse_amount(text: str) -> float | None:
    """'2.5 lakh', '2,50,000', 'ढाई लाख', '1 lakh 20 thousand' -> rupees."""
    text = _norm(text).replace(",", "")
    for word, value in _HINDI_FRACTIONS.items():
        text = text.replace(word, str(value))
    text = re.sub(r"(साढ़े|sadhe)\s*(\d+(?:\.\d+)?)", lambda m: str(float(m.group(2)) + 0.5), text)
    total, found = 0.0, False
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([a-zऀ-ॿ]*)", text):
        found = True
        total += float(number) * _MULTIPLIERS.get(unit, 1)
    return total if found else None


def parse_percent(text: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match or float(match.group()) > 100:
        return None
    return float(match.group())


def parse_date(text: str) -> date | None:
    text = _norm(text)
    for layout in (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d %m %Y",
        "%d %B %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, layout).date()
        except ValueError:
            continue
    return None


def parse_choice(spec: pankh_rules.FactSpec, text: str) -> str | None:
    text = _norm(text)
    compact = text.replace(".", "").replace(" ", "")
    if spec.name == "education_level":
        for key, names in _COURSES.items():
            for name in names:
                if (
                    text == name
                    or compact == name.replace(".", "").replace(" ", "")
                    or re.search(rf"(^|\s){re.escape(name)}($|\s)", text)
                ):
                    return key
    if spec.name == "current_mota_award" and parse_boolean(text) is False:
        return "none"
    for choice in spec.choices:
        labels = {
            choice.key,
            choice.label.lower(),
            *(label.lower() for label in choice.labels.values()),
        }
        if text in labels or any(label and label in text for label in labels if len(label) > 3):
            return choice.key
    return None


def parse_answer(fact: str, text: str) -> Any | None:
    """The value a Student's reply gives for a Fact, or None if it is not an answer."""
    spec = pankh_rules.fact_specs()[fact]
    match spec.kind:
        case pankh_rules.FactKind.BOOLEAN:
            return parse_boolean(text)
        case pankh_rules.FactKind.NUMBER:
            return parse_amount(text) if fact == "family_income" else parse_percent(text)
        case pankh_rules.FactKind.DATE:
            parsed = parse_date(text)
            return parsed.isoformat() if parsed else None
        case pankh_rules.FactKind.CHOICE:
            return parse_choice(spec, text)
    return None


_INTENTS = (
    (
        "renewal",
        (
            "renew",
            "renewal",
            "next year",
            "agle saal",
            "नवीनीकरण",
            "रिन्यू",
            "अगले साल",
        ),
    ),
    (
        "payments",
        (
            "payment",
            "money",
            "paisa",
            "paise",
            "credited",
            "instalment",
            "installment",
            "पैसा",
            "पैसे",
            "भुगतान",
            "किस्त",
            "खाते",
            "amount",
            "received",
        ),
    ),
    (
        "applications",
        (
            "status",
            "application",
            "applied",
            "track",
            "where is",
            "kab",
            "आवेदन",
            "स्थिति",
            "कहाँ",
            "verification",
            "sanction",
        ),
    ),
    (
        "documents",
        (
            "document",
            "certificate",
            "digilocker",
            "दस्तावेज़",
            "दस्तावेज",
            "प्रमाणपत्र",
            "प्रमाण पत्र",
            "problem",
            "attention",
        ),
    ),
    (
        "eligibility",
        (
            "eligible",
            "qualify",
            "which scholarship",
            "scholarship for me",
            "can i get",
            "पात्र",
            "कौन सी",
            "कौनसी",
            "मिल सकती",
            "check",
            "छात्रवृत्ति",
        ),
    ),
    ("greeting", ("hello", "hi", "namaste", "namaskar", "नमस्ते", "नमस्कार", "help", "मदद")),
)

_SCHEME_NAMES = {
    "pre_matric": ("pre matric", "pre-matric", "prematric", "प्री-मैट्रिक", "प्री मैट्रिक"),
    "post_matric": ("post matric", "post-matric", "postmatric", "पोस्ट-मैट्रिक", "पोस्ट मैट्रिक"),
    "top_class": ("top class", "topclass", "टॉप क्लास"),
    "nfst": ("nfst", "fellowship", "फेलोशिप"),
    "nos": ("nos", "overseas", "abroad", "videsh", "विदेश", "प्रवासी"),
}


def classify(text: str) -> str:
    """One of: renewal, payments, applications, documents, scheme:<id>, eligibility, greeting,
    unknown.

    Questions about one's own money, applications or documents come first, so "status of my
    Post-Matric application" is about the application, not about the Scheme.
    """
    text = _norm(text)
    words = set(_words(text))

    def mentions(cues: tuple[str, ...]) -> bool:
        return any(
            (cue in words) if " " not in cue and cue.isascii() else (cue in text) for cue in cues
        )

    for intent, cues in _INTENTS[:4]:
        if mentions(cues):
            return intent
    for scheme_id, names in _SCHEME_NAMES.items():
        if any(name in text for name in names):
            return f"scheme:{scheme_id}"
    for intent, cues in _INTENTS[4:]:
        if mentions(cues):
            return intent
    return "unknown"
