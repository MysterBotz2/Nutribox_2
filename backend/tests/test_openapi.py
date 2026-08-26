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
        "/api/users/me/onboarding-status",
        "/api/users/me/profile-consent",
        "/api/users/me/sensitive-profile",
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
        "/api/meals/{meal_id}/leftover-analysis",
        "/api/scheduled-meals",
        "/api/scheduled-meals/{scheduled_meal_id}",
        "/api/progress/today",
        "/api/progress/daily",
        "/api/progress/weekly",
        "/api/progress/weekly-diagnostics",
        "/api/weight-entries",
        "/api/weight-entries/{entry_id}",
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


def test_openapi_exposes_additive_v2_nutrition_fields() -> None:
    schema = app.openapi()
    nutrition = schema["components"]["schemas"]["PortionNutrition"]["properties"]
    food_source = schema["components"]["schemas"]["FoodSource"]["properties"]

    assert {"saturated_fat_g", "sugars_g", "sodium_mg", "cholesterol_mg", "omega_3_g", "vitamin_b12_mcg"} <= set(nutrition)
    assert "category" in food_source
    assert schema["components"]["schemas"]["NutritionSourceCategory"]["enum"] == [
        "canteen_recipe", "local_database", "USDA", "AI_estimate", "ai_recipe_estimate"
    ]


def test_openapi_keeps_recognition_and_candidate_fields_semantically_separate() -> None:
    schema = app.openapi()
    schemas = schema["components"]["schemas"]

    assert schemas["RecognizedFood"]["properties"]["name"]["maxLength"] == 120
    assert set(schemas["MealAnalysisCandidateResponse"]["properties"]) == {"candidate_id", "name"}


def test_openapi_preserves_r2_profile_privacy_boundaries() -> None:
    """Protect the owner-only, separated R2 profile contract from accidental drift."""
    schema = app.openapi()
    paths = schema["paths"]
    schemas = schema["components"]["schemas"]
    bearer_security = [{"OAuth2PasswordBearer": []}]

    for path, methods in {
        "/api/users/me/profile": ("get", "put"),
        "/api/users/me/profile-consent": ("get", "put"),
        "/api/users/me/sensitive-profile": ("get", "put"),
        "/api/users/me/onboarding-status": ("get",),
    }.items():
        for method in methods:
            assert paths[path][method]["security"] == bearer_security

    assert set(schemas["NutritionProfileUpdateRequest"]["properties"]) == {
        "age", "height_cm", "weight_kg", "activity_level", "nutrition_goal",
        "dietary_restrictions", "allergies", "budget_allotment",
    }
    assert schemas["ProfileConsentState"]["enum"] == [
        "not_asked", "granted", "declined", "withdrawn",
    ]
    sensitive_properties = schemas["SensitiveProfileUpdateRequest"]["properties"]
    assert {"blood_type", "somatotype", "bmi", "age", "allergies"}.isdisjoint(sensitive_properties)
    assert set(schemas["OnboardingStatusResponse"]["properties"]) == {
        "completed", "missing_required_fields",
    }
    assert schemas["OnboardingRequiredField"]["enum"] == [
        "sensitive_consent", "medical_conditions", "smoking_history", "drinking_history", "body_build",
        "allergies", "medical_needs", "lifestyle_diets", "activity_level",
        "budget_allotment", "nutrition_goal",
    ]


def test_openapi_exposes_owner_only_r3a_scheduled_meal_contract() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    schemas = schema["components"]["schemas"]
    bearer_security = [{"OAuth2PasswordBearer": []}]

    for path, methods in {
        "/api/scheduled-meals": ("get", "post"),
        "/api/scheduled-meals/{scheduled_meal_id}": ("get", "put", "delete"),
    }.items():
        for method in methods:
            assert paths[path][method]["security"] == bearer_security

    write_properties = schemas["ScheduledMealCreateRequest"]["properties"]
    assert set(write_properties) == {"scheduled_for", "title", "notes"}
    assert {"user_id", "food_id", "planned_calories", "medical_conditions"}.isdisjoint(write_properties)
    assert paths["/api/scheduled-meals"]["get"]["parameters"][-2]["name"] == "limit"
    assert paths["/api/scheduled-meals/{scheduled_meal_id}"]["delete"]["responses"]["204"]


def test_openapi_exposes_owner_only_r4a_leftover_analysis_contract() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/meals/{meal_id}/leftover-analysis"]
    bearer_security = [{"OAuth2PasswordBearer": []}]

    assert operation["post"]["security"] == bearer_security
    assert operation["get"]["security"] == bearer_security
    assert "multipart/form-data" in operation["post"]["requestBody"]["content"]
    response_schema = operation["post"]["responses"]["201"]["content"]["application/json"]["schema"]
    assert response_schema["$ref"].endswith("/LeftoverAnalysisResponse")
    assert {"initial_nutrition", "leftover_nutrition", "consumed_nutrition", "provenance"} <= set(schema["components"]["schemas"]["LeftoverAnalysisResponse"]["properties"])


def test_openapi_exposes_owner_only_personal_recipe_contract() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    bearer_security = [{"OAuth2PasswordBearer": []}]
    save_path = "/api/meals/analysis-sessions/{analysis_session_id}/components/{component_id}/save-recipe"

    assert paths[save_path]["post"]["security"] == bearer_security
    assert paths[save_path]["post"]["responses"]["201"]["content"]["application/json"]["schema"]["$ref"].endswith("/UserRecipeResponse")
    for method in ("get", "delete"):
        assert paths["/api/users/me/recipes/{recipe_id}"][method]["security"] == bearer_security
    assert paths["/api/users/me/recipes"]["get"]["security"] == bearer_security
    ingredient = schema["components"]["schemas"]["UserRecipeIngredientResponse"]["properties"]
    assert {"name", "normalized_proportion", "nutrition_source", "resolved_reference", "ingredient_source", "weight_source"} == set(ingredient)


def test_openapi_exposes_personal_recipe_reuse_session_contract() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    bearer_or_device_security = [{"OAuth2PasswordBearer": []}, {"APIKeyHeader": []}]
    base = "/api/meals/analysis-sessions/{analysis_session_id}/components/{component_id}"

    for suffix in ("use-recipe", "review-recipe", "analyze-as-new"):
        assert paths[f"{base}/{suffix}"]["post"]["security"] == bearer_or_device_security
    assert "RequiresRecipeConfirmationMealAnalysis" in schema["components"]["schemas"]
    component = schema["components"]["schemas"]["MealAnalysisComponentResponse"]["properties"]
    assert "recipe_matches" in component


def test_openapi_exposes_device_authorized_meal_operations_and_safe_device_identity() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    schemas = schema["components"]["schemas"]
    bearer_or_device_security = [{"OAuth2PasswordBearer": []}, {"APIKeyHeader": []}]

    assert schemas["DeviceIdentityResponse"]["properties"]["owner_first_name"]["maxLength"] == 80
    assert {"email", "last_name", "token_hash", "pairing_code", "device_token"}.isdisjoint(
        schemas["DeviceIdentityResponse"]["properties"]
    )
    assert paths["/api/device/me"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/DeviceIdentityResponse")
    for path, method in {
        "/api/meals/analyze": "post",
        "/api/meals": "post",
        "/api/meals/analysis-sessions/{analysis_session_id}/selections": "post",
        "/api/meals/analysis-sessions/{analysis_session_id}/components/{component_id}/ingredients": "put",
        "/api/meals/analysis-sessions/{analysis_session_id}/components/{component_id}/ingredients/selections": "post",
    }.items():
        assert paths[path][method]["security"] == bearer_or_device_security
