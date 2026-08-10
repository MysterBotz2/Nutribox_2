from fastapi.testclient import TestClient

from app.main import app
from app.routers import health

client = TestClient(app)


def test_root_returns_service_information() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "Nutri-Box API", "status": "running"}


def test_health_returns_healthy_status(monkeypatch) -> None:
    monkeypatch.setattr(health.database, "check_database_connection", lambda: True)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}


def test_health_returns_safe_unhealthy_response(monkeypatch) -> None:
    monkeypatch.setattr(health.database, "check_database_connection", lambda: False)

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy", "database": "disconnected"}


def test_documentation_endpoints_are_available() -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
