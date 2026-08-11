import json

from app.cli.export_openapi import export_openapi
from app.main import app


def test_openapi_has_v1_metadata_routes_and_oauth2_security() -> None:
    schema = app.openapi()

    assert schema["info"]["version"] == "1.0.0"
    expected_paths = {
        "/",
        "/api/health",
        "/api/auth/register",
        "/api/auth/token",
        "/api/users/me",
        "/api/users/me/profile",
        "/api/users/me/targets",
        "/api/device/simulate",
        "/api/ai/recognize-food",
        "/api/ai/coach",
        "/api/nutrition/search",
        "/api/nutrition/{food_id}",
        "/api/nutrition/calculate",
        "/api/meals/analyze",
        "/api/meals",
        "/api/meals/{meal_id}",
        "/api/progress/today",
        "/api/progress/daily",
        "/api/progress/weekly",
        "/api/progress/summary",
        "/api/progress/target-status",
    }
    assert expected_paths <= set(schema["paths"])
    assert schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["type"] == "oauth2"
    assert "multipart/form-data" in schema["paths"]["/api/ai/recognize-food"]["post"]["requestBody"]["content"]


def test_openapi_export_is_valid_json_and_contains_no_configuration_values(tmp_path) -> None:
    output_path = export_openapi(tmp_path / "openapi.json")
    exported = json.loads(output_path.read_text(encoding="utf-8"))

    assert exported == app.openapi()
    serialized = output_path.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" not in serialized
    assert "JWT_SECRET_KEY" not in serialized
