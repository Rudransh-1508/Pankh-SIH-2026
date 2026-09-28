"""Deciding whether two written names belong to the same person.

Names of tribal students are written many ways across offices: different transliterations
(Hansda, Hansdah), scripts (सुनीता, Sunita), orders (Tirkey Rinki), honorifics (Km., Shri) and
missing surnames. Names are reduced to sound-alike keys before comparing, word by word and in
any order.
"""

import re
import unicodedata
from dataclasses import dataclass

from indic_transliteration import sanscript
from rapidfuzz.distance import JaroWinkler

# Words that say nothing about who someone is.
_FILLERS = {
    "shri",
    "sri",
    "shree",
    "smt",
    "shrimati",
    "km",
    "kumari",
    "kumar",
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "md",
    "mohd",
}

# Spellings that sound the same in Indian names, applied in order.
_SOUND_ALIKES = (
    ("ph", "f"),
    ("bh", "b"),
    ("kh", "k"),
    ("gh", "g"),
    ("th", "t"),
    ("dh", "d"),
    ("sh", "s"),
    ("ch", "c"),
    ("jh", "j"),
    ("w", "v"),
    ("z", "j"),
    ("q", "k"),
    ("x", "ks"),
    ("ck", "k"),
    ("ee", "i"),
    ("oo", "u"),
    ("aa", "a"),
    ("ou", "u"),
    ("ai", "e"),
    ("ay", "e"),
)


@dataclass(frozen=True)
class NameMatch:
    score: float
    """0 (different people) to 1 (same name, however written)."""
    left_key: str
    right_key: str

    @property
    def is_match(self) -> bool:
        return self.score >= MATCH_THRESHOLD


MATCH_THRESHOLD = 0.9


_CONSONANT = "[bcdfgjklmnpqrstvwxyz]h?"


def _delete_schwas(word: str) -> str:
    """Drop the inherent 'a' Hindi does not pronounce: keraketta -> kerketta.

    Transliterating Devanagari writes an 'a' after every bare consonant. Hindi drops it
    between a vowel-consonant and a consonant-vowel, so that is where it is removed.
    """
    pattern = re.compile(rf"(?<=[aeiou])({_CONSONANT})a(?={_CONSONANT}[aeiou])")
    previous = None
    while previous != word:
        previous, word = word, pattern.sub(r"\1", word, count=1)
    return word


def _is_devanagari(ch: str) -> bool:
    return "ऀ" <= ch <= "ॿ"


def _latin(name: str) -> str:
    if any(_is_devanagari(ch) for ch in name):
        name = sanscript.transliterate(name, sanscript.DEVANAGARI, sanscript.ITRANS)
        # Anusvara and nasal marks sound as n; case in ITRANS only marks vowel length.
        name = name.replace("M", "n").replace(".n", "").replace("~N", "n").lower()
        name = " ".join(_delete_schwas(word) for word in name.split())
    name = unicodedata.normalize("NFKD", name)
    return "".join(ch for ch in name if not unicodedata.combining(ch)).lower()


def _key(word: str) -> str:
    for spelling, sound in _SOUND_ALIKES:
        word = word.replace(spelling, sound)
    word = re.sub(r"(ey|ie|y|e)$", "i", word)
    word = re.sub(r"([aeiou])h$", r"\1", word)
    word = re.sub(r"(.)\1+", r"\1", word)
    # Devanagari transliteration keeps a final inherent vowel (रमेश -> ramesha); drop it everywhere.
    return re.sub(r"(?<=[^aeiou])a$", "", word) or word


def name_key(name: str) -> tuple[str, ...]:
    words = re.findall(r"[a-z]+", _latin(name))
    return tuple(_key(word) for word in words if word not in _FILLERS)


def match_names(left: str, right: str) -> NameMatch:
    a, b = name_key(left), name_key(right)
    if not a or not b:
        return NameMatch(0.0, " ".join(a), " ".join(b))
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    # Every word must match: a shared surname cannot make up for a different first name,
    # since siblings share surnames. The weakest word decides.
    remaining = list(longer)
    score = 1.0
    for word in shorter:
        best = max(remaining, key=lambda other: JaroWinkler.similarity(word, other))
        score = min(score, JaroWinkler.similarity(word, best))
        remaining.remove(best)
    if len(shorter) < len(longer):
        # A missing surname is common, but it leaves real doubt about who this is.
        score *= 0.85 ** (len(longer) - len(shorter))
    return NameMatch(round(score, 3), " ".join(a), " ".join(b))
