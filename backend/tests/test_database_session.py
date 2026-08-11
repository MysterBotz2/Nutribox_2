import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import database
from app.main import app
from conftest import register_and_login


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_request_database_session_commits_after_success(monkeypatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_request_database_session_rolls_back_after_error(monkeypatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()

    assert next(dependency) is session
    with pytest.raises(RuntimeError):
        dependency.throw(RuntimeError("request failed"))

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True


def test_authenticated_target_write_commits_across_request_sessions(
    database_session: Session, jwt_configuration: None, monkeypatch
) -> None:
    connection = database_session.get_bind()

    def test_session_factory() -> Session:
        return Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

    monkeypatch.setattr(database, "SessionLocal", test_session_factory)
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        created = client.put(
            "/api/users/me/targets",
            json={"calories": "123.456", "source_type": "manual"},
            headers=headers,
        )
        retrieved = client.get("/api/users/me/targets", headers=headers)

    assert created.status_code == 200
    assert retrieved.status_code == 200
    assert retrieved.json()["calories"] == "123.456"
