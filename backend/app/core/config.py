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

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


settings = get_settings()
