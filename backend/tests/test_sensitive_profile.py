from fastapi.testclient import TestClient

from app.main import app
from app.routers.ai import get_nutrition_coach_service
from app.routers.users import get_sensitive_profile_service
from app.services.nutrition_coach_provider import (
    NutritionCoachContext,
    NutritionCoachProvider,
    NutritionCoachResult,
)
from conftest import register_and_login


class CapturingCoachProvider(NutritionCoachProvider):
    def __init__(self) -> None:
        self.contexts: list[NutritionCoachContext] = []

    async def generate_guidance(self, context: NutritionCoachContext) -> NutritionCoachResult:
        self.contexts.append(context)
        return NutritionCoachResult(message="Safe.", highlights=("Safe.",), provider="capture")


def granted_consent() -> dict[str, str]:
    return {
        "sensitive_storage": "granted",
        "personalization": "not_asked",
        "ai_context": "not_asked",
    }


def valid_sensitive_profile() -> dict[str, object]:
    return {
        "medical_conditions": ["diabetes", "other"],
        "medical_conditions_other": "A user-declared condition",
        "pregnancy_status": "pregnant",
        "pregnancy_duration_value": 12,
        "pregnancy_duration_unit": "weeks",
        "pregnancy_due_date": "2027-01-10",
        "smoking_status": "never",
        "smoking_methods": ["none"],
        "drinking_status": "former",
        "drinking_frequency": "rarely",
        "average_alcohol_intake": "one_to_two",
        "last_alcohol_consumption": "more_than_30_days_ago",
        "alcohol_types": ["wine"],
        "body_build": "average",
        "weight_status": "normal_weight",
        "ethnicity": "filipino",
        "medical_needs": ["low_sodium", "gluten_free"],
    }


def test_sensitive_resources_require_authentication(client: TestClient) -> None:
    assert client.get("/api/users/me/profile-consent").status_code == 401
    assert client.put("/api/users/me/profile-consent", json=granted_consent()).status_code == 401
    assert client.get("/api/users/me/sensitive-profile").status_code == 401
    assert client.put("/api/users/me/sensitive-profile", json={}).status_code == 401


def test_consent_defaults_not_asked_and_sensitive_write_requires_grant(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    default = client.get("/api/users/me/profile-consent", headers=headers)
    rejected = client.put("/api/users/me/sensitive-profile", json={}, headers=headers)

    assert default.status_code == 200
    assert default.json() == {
        "user_id": default.json()["user_id"],
        "sensitive_storage": "not_asked",
        "personalization": "not_asked",
        "ai_context": "not_asked",
        "updated_at": None,
    }
    assert rejected.status_code == 403
    assert rejected.json() == {"detail": "Sensitive profile storage consent must be granted."}


def test_sensitive_profile_is_owner_scoped_and_preserves_none_vs_null(
    client: TestClient, jwt_configuration: None
) -> None:
    first, first_headers = register_and_login(client, "first-sensitive@example.com")
    _, second_headers = register_and_login(client, "second-sensitive@example.com")
    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=first_headers).status_code == 200
    created = client.put(
        "/api/users/me/sensitive-profile", json=valid_sensitive_profile(), headers=first_headers
    )
    second_read = client.get("/api/users/me/sensitive-profile", headers=second_headers)

    assert created.status_code == 200
    assert created.json()["user_id"] == first["id"]
    assert created.json()["medical_conditions"] == ["diabetes", "other"]
    assert created.json()["smoking_methods"] == ["none"]
    assert second_read.status_code == 404
    assert client.put(
        "/api/users/me/sensitive-profile",
        json={"medical_conditions": ["none"]},
        headers=second_headers,
    ).status_code == 403

    cleared = client.put("/api/users/me/sensitive-profile", json={}, headers=first_headers)
    assert cleared.status_code == 200
    assert cleared.json()["medical_conditions"] is None
    assert cleared.json()["pregnancy_status"] is None


def test_storage_consent_declined_or_withdrawn_rejects_writes_and_withdrawal_clears_context(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=valid_sensitive_profile(), headers=headers).status_code == 200

    declined = {**granted_consent(), "sensitive_storage": "declined"}
    assert client.put("/api/users/me/profile-consent", json=declined, headers=headers).status_code == 200
    assert client.get("/api/users/me/sensitive-profile", headers=headers).status_code == 404
    assert client.put("/api/users/me/sensitive-profile", json={}, headers=headers).status_code == 403

    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=valid_sensitive_profile(), headers=headers).status_code == 200
    withdrawn = {**granted_consent(), "sensitive_storage": "withdrawn"}
    assert client.put("/api/users/me/profile-consent", json=withdrawn, headers=headers).status_code == 200
    assert client.get("/api/users/me/sensitive-profile", headers=headers).status_code == 404
    assert client.put("/api/users/me/sensitive-profile", json={}, headers=headers).status_code == 403


def test_personalization_or_ai_withdrawal_does_not_delete_context(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=valid_sensitive_profile(), headers=headers).status_code == 200
    changed = {
        "sensitive_storage": "granted",
        "personalization": "withdrawn",
        "ai_context": "withdrawn",
    }
    assert client.put("/api/users/me/profile-consent", json=changed, headers=headers).status_code == 200
    preserved = client.get("/api/users/me/sensitive-profile", headers=headers)
    assert preserved.status_code == 200
    assert preserved.json()["body_build"] == "average"


def test_sensitive_profile_validates_client_options_and_rejects_unsupported_fields(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=headers).status_code == 200
    assert client.put(
        "/api/users/me/sensitive-profile",
        json={"medical_conditions": ["none", "diabetes"]},
        headers=headers,
    ).status_code == 422
    assert client.put(
        "/api/users/me/sensitive-profile",
        json={"smoking_status": "last_6_months", "smoking_methods": ["none", "vaping"]},
        headers=headers,
    ).status_code == 422
    assert client.put(
        "/api/users/me/sensitive-profile",
        json={"pregnancy_status": "postpartum", "pregnancy_duration_value": 2, "pregnancy_duration_unit": "weeks"},
        headers=headers,
    ).status_code == 422


def test_sensitive_profile_normalizes_collections_and_canonicalizes_never_states(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=headers).status_code == 200

    response = client.put(
        "/api/users/me/sensitive-profile",
        json={
            "medical_conditions": [" Hypertension ", "hypertension"],
            "smoking_status": "never",
            "smoking_methods": ["vaping"],
            "drinking_status": "never",
            "drinking_frequency": "daily",
            "average_alcohol_intake": "five_or_more",
            "last_alcohol_consumption": "last_24_hours",
            "alcohol_types": ["beer"],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["medical_conditions"] == ["hypertension"]
    assert response.json()["smoking_methods"] == ["none"]
    assert response.json()["drinking_frequency"] is None
    assert response.json()["average_alcohol_intake"] is None
    assert response.json()["last_alcohol_consumption"] == "never"
    assert response.json()["alcohol_types"] == []
    assert client.put(
        "/api/users/me/sensitive-profile",
        json={"body_build": "ectomorph"},
        headers=headers,
    ).status_code == 422
    assert client.put(
        "/api/users/me/sensitive-profile",
        json={"blood_type": "O+", "bmi_weight_status": "normal"},
        headers=headers,
    ).status_code == 422


def test_budget_remains_in_ordinary_profile_without_duplicating_existing_fields(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    response = client.put(
        "/api/users/me/profile",
        json={
            "activity_level": "highly_active",
            "nutrition_goal": "lose_weight",
            "allergies": ["eggs", "tree nuts"],
            "dietary_restrictions": ["vegan", "halal"],
            "budget_allotment": "php_100_to_500",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["activity_level"] == "highly_active"
    assert response.json()["budget_allotment"] == "php_100_to_500"
    assert response.json()["allergies"] == ["eggs", "tree nuts"]


def test_sensitive_context_is_not_forwarded_to_coach(
    client: TestClient, jwt_configuration: None
) -> None:
    from app.services.nutrition_coach_selector import get_nutrition_coach_provider

    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile-consent", json=granted_consent(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=valid_sensitive_profile(), headers=headers).status_code == 200
    provider = CapturingCoachProvider()
    app.dependency_overrides[get_nutrition_coach_provider] = lambda: provider
    try:
        response = client.post("/api/ai/coach", json={}, headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    context = provider.contexts[0]
    assert not any(
        hasattr(context, field)
        for field in ("medical_conditions", "pregnancy_status", "smoking_status", "drinking_status", "ethnicity")
    )
    assert context.profile is None
