import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType


class InvalidPhoneNumber(ValueError):
    pass


def normalise_indian_mobile(raw: str) -> str:
    """Return an Indian mobile number in E.164 form (+91XXXXXXXXXX), or raise."""
    try:
        number = phonenumbers.parse(raw, "IN")
    except NumberParseException as error:
        raise InvalidPhoneNumber("Enter a valid 10-digit mobile number") from error
    if number.country_code != 91 or not phonenumbers.is_valid_number(number):
        raise InvalidPhoneNumber("Enter a valid Indian mobile number")
    if phonenumbers.number_type(number) not in (
        PhoneNumberType.MOBILE,
        PhoneNumberType.FIXED_LINE_OR_MOBILE,
    ):
        raise InvalidPhoneNumber("Enter a mobile number, not a landline")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
