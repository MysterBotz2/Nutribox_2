from app.core.config import ENV_FILE, Settings


def test_settings_resolve_env_file_from_backend_directory() -> None:
    assert ENV_FILE.name == ".env"
    assert ENV_FILE.parent.name == "backend"


def test_operating_system_environment_overrides_env_file(monkeypatch) -> None:
    expected_url = "postgresql+psycopg://environment_user:password@host:5432/database"
    monkeypatch.setenv("DATABASE_URL", expected_url)

    assert Settings().database_url == expected_url


def test_coach_provider_configuration_defaults_to_mock_and_honors_environment(monkeypatch) -> None:
    assert Settings().nutrition_coach_provider == "mock"
    monkeypatch.setenv("NUTRITION_COACH_PROVIDER", "custom")

    assert Settings().nutrition_coach_provider == "custom"
