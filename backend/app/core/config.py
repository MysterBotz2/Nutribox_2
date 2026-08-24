from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from typing import Annotated

BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIRECTORY / ".env"


class Settings(BaseSettings):
    """Configuration loaded from OS environment variables and backend/.env."""

    database_url: str | None = None
    test_database_url: str | None = None
    food_recognition_provider: str = "mock"
    food_recognition_max_upload_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    gemini_timeout_seconds: int = Field(default=20, gt=0, le=120)
    usda_fdc_enabled: bool = False
    usda_fdc_api_key: str | None = None
    usda_fdc_base_url: str = "https://api.nal.usda.gov/fdc/v1"
    usda_fdc_timeout_seconds: int = Field(default=10, gt=0, le=60)
    nutrition_coach_provider: str = "mock"
    nutrition_coach_gemini_api_key: str | None = None
    nutrition_coach_gemini_model: str | None = None
    nutrition_coach_gemini_timeout_seconds: int = Field(default=20, gt=0, le=120)
    device_pairing_secret: str | None = None
    device_pairing_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    meal_analysis_session_ttl_minutes: int = Field(default=30, ge=1, le=1440)
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)
    nutribox_demo_password: str | None = None
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: str | list[str] | None) -> list[str]:
        """Parse a comma-separated explicit browser-origin allowlist."""
        if value is None:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


settings = get_settings()
