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
    official_session_ttl: timedelta = timedelta(hours=8)

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

    # JAGO's language model: any provider with an OpenAI-compatible chat completions API.
    # Unset, JAGO answers with its own grounded intents and needs no model at all.
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # Temporal runs long-lived Agent work such as chasing stalled applications. Unset, nothing is
    # scheduled; the ministry can still run a sweep by hand.
    temporal_address: str | None = None
    temporal_namespace: str = "default"
    chasing_task_queue: str = "pankh-chasing"

    # Proofs are signed with an Ed25519 key. Unset, a key is derived from secret_key.
    proof_signing_key: str | None = None
    proof_ttl: timedelta = timedelta(days=365)

    # Uploaded Documents: encrypted photos in object storage. "file" keeps them in a local
    # directory (development and tests); "s3" uses any S3-compatible store (SeaweedFS locally).
    object_store: Literal["file", "s3"] = "file"
    object_store_path: str = "var/objects"
    s3_bucket: str = "pankh-documents"
    s3_endpoint_url: str | None = None
    s3_region: str = "ap-south-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    # A base64 AES-256 key wrapping each photo's own key. Unset, one is derived from secret_key.
    document_master_key: str | None = None
    document_link_ttl: timedelta = timedelta(minutes=5)
    document_max_bytes: int = 8 * 1024 * 1024
    document_uploads_per_day: int = 20
    # Photos are deleted this long after the academic session they were uploaded for ends.
    document_retention: timedelta = timedelta(days=365)

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
