from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app, configure_cors


def test_configured_cors_origin_and_authorization_preflight_are_allowed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", ["http://localhost:5173"])
    from fastapi import FastAPI

    cors_app = FastAPI()
    configure_cors(cors_app, settings.cors_allowed_origins)
    response = TestClient(cors_app).options(
        "/api/users/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Authorization" in response.headers["access-control-allow-headers"]


def test_unknown_cors_origin_is_not_granted() -> None:
    response = TestClient(app).options(
        "/api/users/me",
        headers={
            "Origin": "http://unknown.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "*"
    assert response.headers.get("access-control-allow-origin") != "http://unknown.example"
