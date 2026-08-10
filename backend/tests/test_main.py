from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_service_information() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "Nutri-Box API", "status": "running"}


def test_health_returns_healthy_status() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_documentation_endpoints_are_available() -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
