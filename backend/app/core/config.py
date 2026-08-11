from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    nutrition_coach_provider: str = "mock"
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


settings = get_settings()
