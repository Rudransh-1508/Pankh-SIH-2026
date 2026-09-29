import logging
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger(__name__)


class SmsSender(Protocol):
    async def send_otp(self, phone: str, code: str) -> None: ...

    async def send_text(self, phone: str, text: str) -> None: ...


class ConsoleSmsSender:
    """Development sender: writes the code to the server log instead of sending an SMS.

    Real delivery goes through Exotel once DLT sender and template registration is approved.
    """

    async def send_otp(self, phone: str, code: str) -> None:
        logger.warning("OTP for %s is %s (console SMS sender, development only)", phone, code)

    async def send_text(self, phone: str, text: str) -> None:
        logger.warning("SMS to %s: %s (console SMS sender, development only)", phone, text)


def get_sms_sender() -> SmsSender:
    match get_settings().sms_sender:
        case "console":
            return ConsoleSmsSender()
