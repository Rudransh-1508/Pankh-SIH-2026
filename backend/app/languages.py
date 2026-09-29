"""The languages Pankh speaks: the app, JAGO, voice, letters and outreach all use this list.

Every text table keyed by language (JAGO, letters, the phone line, outreach, and the rules
package's questions) has an entry for each of them; tests check this.
"""

from typing import Literal

Language = Literal["en", "hi", "bn", "gu", "mr", "or"]
LANGUAGES: tuple[Language, ...] = ("en", "hi", "bn", "gu", "mr", "or")

NAMES: dict[Language, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "mr": "Marathi",
    "or": "Odia",
}

# Sarvam's language codes for speech. Sarvam writes Odia as "od"; ISO 639-1 (used everywhere
# else, including the app's locales) writes it as "or".
SPEECH: dict[Language, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
    "or": "od-IN",
}
