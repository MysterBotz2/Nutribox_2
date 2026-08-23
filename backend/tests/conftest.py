from collections.abc import Generator
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import Base
from app.database.database import get_db
from app.main import app


@pytest.fixture(autouse=True)
def force_mock_food_recognition_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep normal tests independent of a developer's real-provider .env settings."""
    monkeypatch.setattr(settings, "food_recognition_provider", "mock")
    monkeypatch.setattr(settings, "nutrition_coach_provider", "mock")


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    test_database_url = settings.test_database_url
    if not test_database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests.")
    if test_database_url == settings.database_url:
        pytest.skip("TEST_DATABASE_URL must be different from DATABASE_URL.")

    test_engine = create_engine(test_database_url)
    with test_engine.connect() as connection:
        transaction = connection.begin()
        Base.metadata.create_all(connection)
        session = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
    test_engine.dispose()


@pytest.fixture
def client(database_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def jwt_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", secrets.token_urlsafe(48))
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(settings, "access_token_expire_minutes", 30)


def register_and_login(client: TestClient, email: str = "user@example.com") -> tuple[dict, dict[str, str]]:
    registration = {
        "email": email,
        "password": "prototype-password",
        "first_name": "Test",
        "last_name": "User",
    }
    registered = client.post("/api/auth/register", json=registration)
    assert registered.status_code == 201
    token = client.post(
        "/api/auth/token",
        data={"username": email, "password": registration["password"]},
    )
    assert token.status_code == 200
    return registered.json(), {"Authorization": f"Bearer {token.json()['access_token']}"}


@pytest.fixture
def auth_headers(client: TestClient, jwt_configuration: None) -> dict[str, str]:
    _, headers = register_and_login(client)
    return headers
