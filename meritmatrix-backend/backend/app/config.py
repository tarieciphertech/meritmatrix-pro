"""
Centralized application configuration.

All configuration is sourced from environment variables (see .env.example).
No secrets or deployment-specific values are hard-coded here.
"""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Core application ---
    APP_NAME: str = "MeritMatrix Pro 2.0"
    ENVIRONMENT: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # Production/staging MUST use PostgreSQL. SQLite is only ever used
    # automatically as a local fallback for the /health smoke-test when no
    # DATABASE_URL is configured at all (see database.py), never in
    # staging/production environments.
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://meritmatrix:meritmatrix@localhost:5432/meritmatrix"
    )
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=20)
    DATABASE_ECHO: bool = Field(default=False)

    # --- Security / Auth ---
    SECRET_KEY: str = Field(default="CHANGE_ME_INSECURE_DEV_ONLY_SECRET_KEY")
    JWT_SECRET: str = Field(default="CHANGE_ME_INSECURE_DEV_ONLY_JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # --- CORS ---
    CORS_ORIGINS: str = Field(default="http://localhost:5173")

    # --- Frontend ---
    FRONTEND_URL: str = Field(default="http://localhost:5173")

    # --- Email (SMTP) — provider-agnostic, used by parent verification / notifications ---
    SMTP_HOST: str = Field(default="")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM_EMAIL: str = Field(default="no-reply@meritmatrix.local")

    # --- SMS (OTP provider) — provider-agnostic ---
    SMS_PROVIDER: str = Field(default="mock")  # mock | twilio | africas_talking | ...
    OTP_MOCK_STATIC_CODE: str = Field(default="")  # dev/test only, never set in prod

    # --- Logging ---
    LOG_LEVEL: str = Field(default="INFO")

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got {v!r}")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()
