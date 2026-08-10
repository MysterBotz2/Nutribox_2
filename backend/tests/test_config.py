from app.core.config import ENV_FILE, Settings


def test_settings_resolve_env_file_from_backend_directory() -> None:
    assert ENV_FILE.name == ".env"
    assert ENV_FILE.parent.name == "backend"


def test_operating_system_environment_overrides_env_file(monkeypatch) -> None:
    expected_url = "postgresql+psycopg://environment_user:password@host:5432/database"
    monkeypatch.setenv("DATABASE_URL", expected_url)

    assert Settings().database_url == expected_url
