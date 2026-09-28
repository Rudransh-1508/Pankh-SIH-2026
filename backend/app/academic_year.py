from datetime import date

# Applications for a session open from April (Pre-Matric registration opens 1 April), so from
# April onwards the upcoming session's Rules are the ones a Student needs.
SESSION_SWITCH_MONTH = 4


def current_academic_year(today: date | None = None) -> int:
    today = today or date.today()
    return today.year if today.month >= SESSION_SWITCH_MONTH else today.year - 1


def label(academic_year: int) -> str:
    return f"{academic_year}-{(academic_year + 1) % 100:02d}"
