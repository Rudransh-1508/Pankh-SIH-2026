from datetime import timedelta
from functools import cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SECRET = "development-only-secret-change-me-0123456789"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PANKH_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://pankh:pankh@localhost:5433/pankh"
    secret_key: str = DEVELOPMENT_SECRET
    cors_origins: list[str] = ["http://localhost:3000"]

    access_token_ttl: timedelta = timedelta(minutes=15)
    refresh_token_ttl: timedelta = timedelta(days=60)

    otp_ttl: timedelta = timedelta(minutes=5)
    otp_max_attempts: int = 5
    otp_resend_cooldown: timedelta = timedelta(seconds=30)
    otp_max_per_hour: int = 5
    sms_sender: Literal["console"] = "console"

    # Source Systems and Data Sources. Defaults point at the local simulators.
    digilocker_url: str = "http://localhost:8100/digilocker"
    digilocker_client_id: str = "PANKH-SIM"
    digilocker_client_secret: str = "pankh-simulator-secret"
    digilocker_redirect_uri: str = "pankh://digilocker/callback"
    registers_url: str = "http://localhost:8100"
    registers_api_key: str = "pankh-simulator-key"

    # Proofs are signed with an Ed25519 key. Unset, a key is derived from secret_key.
    proof_signing_key: str | None = None
    proof_ttl: timedelta = timedelta(days=365)

    @model_validator(mode="after")
    def _require_real_secret_outside_development(self) -> "Settings":
        if self.environment == "production" and self.secret_key == DEVELOPMENT_SECRET:
            raise ValueError("PANKH_SECRET_KEY must be set in production")
        if len(self.secret_key) < 32:
            raise ValueError("PANKH_SECRET_KEY must be at least 32 characters")
        return self


@cache
def get_settings() -> Settings:
    return Settings()
