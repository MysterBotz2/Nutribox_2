from fastapi.testclient import TestClient

from conftest import register_and_login


def profile_payload() -> dict[str, object]:
    return {
        "activity_level": "highly_active",
        "nutrition_goal": "maintain_weight",
        "allergies": [],
        "dietary_restrictions": [],
        "budget_allotment": "php_100_to_500",
    }


def consent_payload(storage: str = "granted") -> dict[str, str]:
    return {
        "sensitive_storage": storage,
        "personalization": "not_asked",
        "ai_context": "not_asked",
    }


def sensitive_payload() -> dict[str, object]:
    return {
        "medical_conditions": ["none"],
        "smoking_status": "never",
        "smoking_method": "none",
        "drinking_status": "never",
        "body_build": "average",
        "medical_needs": [],
        # Optional pregnancy/postpartum and ethnicity remain absent.
    }


def status(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.get("/api/users/me/onboarding-status", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_onboarding_status_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/users/me/onboarding-status").status_code == 401


def test_new_user_is_incomplete_with_stable_missing_order(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert status(client, headers) == {
        "completed": False,
        "missing_required_fields": [
            "allergies",
            "lifestyle_diets",
            "activity_level",
            "budget_allotment",
            "nutrition_goal",
            "medical_conditions",
            "smoking_history",
            "drinking_history",
            "body_build",
            "medical_needs",
        ],
    }


def test_ordinary_fields_and_null_semantics_contribute_to_completion(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile", json=profile_payload(), headers=headers).status_code == 200
    result = status(client, headers)
    assert result["missing_required_fields"] == [
        "medical_conditions", "smoking_history", "drinking_history", "body_build", "medical_needs"
    ]

    assert client.put(
        "/api/users/me/profile",
        json={**profile_payload(), "allergies": None},
        headers=headers,
    ).status_code == 200
    assert "allergies" in status(client, headers)["missing_required_fields"]


def test_sensitive_fields_require_granted_storage_consent_and_complete_with_explicit_none(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile", json=profile_payload(), headers=headers).status_code == 200
    assert client.put("/api/users/me/profile-consent", json=consent_payload(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=sensitive_payload(), headers=headers).status_code == 200

    result = status(client, headers)
    assert result == {"completed": True, "missing_required_fields": []}


def test_optional_sensitive_fields_may_be_null_and_status_never_returns_values(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile", json=profile_payload(), headers=headers).status_code == 200
    assert client.put("/api/users/me/profile-consent", json=consent_payload(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=sensitive_payload(), headers=headers).status_code == 200
    result = status(client, headers)

    assert result["completed"] is True
    assert set(result) == {"completed", "missing_required_fields"}
    serialized = str(result)
    assert "blood_type" not in serialized and "somatotype" not in serialized
    assert "medical_conditions" not in serialized or "medical_conditions" not in result


def test_withdrawal_makes_status_incomplete_without_breaking_login_or_ordinary_routes(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put("/api/users/me/profile", json=profile_payload(), headers=headers).status_code == 200
    assert client.put("/api/users/me/profile-consent", json=consent_payload(), headers=headers).status_code == 200
    assert client.put("/api/users/me/sensitive-profile", json=sensitive_payload(), headers=headers).status_code == 200
    assert status(client, headers)["completed"] is True

    assert client.put("/api/users/me/profile-consent", json=consent_payload("withdrawn"), headers=headers).status_code == 200
    result = status(client, headers)
    assert result["completed"] is False
    assert result["missing_required_fields"] == [
        "medical_conditions", "smoking_history", "drinking_history", "body_build", "medical_needs"
    ]
    assert client.get("/api/users/me", headers=headers).status_code == 200
    assert client.get("/api/users/me/profile", headers=headers).status_code == 200
