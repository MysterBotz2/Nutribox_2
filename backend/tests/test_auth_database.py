from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.food import Food
from app.models.meal import Meal
from app.models.user import User
from app.services.security import create_access_token
from conftest import register_and_login


def create_test_food() -> Food:
    return Food(
        name="Authenticated Test Food",
        category="test",
        calories_per_100g=Decimal("100.00"),
        protein_g_per_100g=Decimal("10.000"),
        carbohydrates_g_per_100g=Decimal("20.000"),
        fat_g_per_100g=Decimal("3.000"),
        fiber_g_per_100g=Decimal("2.000"),
        source_name="Synthetic test source",
        source_reference="test-only",
        is_verified=False,
    )


def test_registers_hashed_user_and_never_returns_hash(
    database_session: Session, client: TestClient
) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "  PERSON@Example.COM ",
            "password": "prototype-password",
            "first_name": "Person",
            "last_name": "Example",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "person@example.com"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    stored = database_session.query(User).one()
    assert stored.password_hash != "prototype-password"
    assert stored.password_hash.startswith("$argon2")


def test_duplicate_normalized_email_is_rejected(client: TestClient) -> None:
    first = {
        "email": "person@example.com",
        "password": "prototype-password",
        "first_name": "Person",
        "last_name": "Example",
    }
    assert client.post("/api/auth/register", json=first).status_code == 201
    duplicate = {**first, "email": "  PERSON@EXAMPLE.COM "}
    response = client.post("/api/auth/register", json=duplicate)

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with this email already exists."}


def test_login_uses_generic_failure_and_token_contains_subject_and_expiry(
    client: TestClient, jwt_configuration: None
) -> None:
    user, _ = register_and_login(client)
    success = client.post(
        "/api/auth/token",
        data={"username": user["email"], "password": "prototype-password"},
    )
    wrong_password = client.post(
        "/api/auth/token", data={"username": user["email"], "password": "wrong-password"}
    )
    unknown_email = client.post(
        "/api/auth/token",
        data={"username": "missing@example.com", "password": "wrong-password"},
    )

    assert success.status_code == 200
    payload = jwt.decode(
        success.json()["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert payload["sub"] == str(user["id"])
    assert "exp" in payload
    assert success.json()["token_type"] == "bearer"
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": "Incorrect email or password."}


def test_invalid_expired_and_missing_tokens_are_rejected(
    client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    expired = jwt.encode(
        {"sub": str(user["id"]), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/users/me", headers={"Authorization": headers["Authorization"] + "tampered"}).status_code == 401


def test_current_user_and_inactive_account_protection(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]

    stored = database_session.get(User, user["id"])
    assert stored is not None
    stored.is_active = False
    database_session.flush()
    assert client.get("/api/users/me", headers=headers).status_code == 401


def test_profile_is_created_replaced_and_scoped_to_current_user(
    client: TestClient, jwt_configuration: None
) -> None:
    first, first_headers = register_and_login(client, "first@example.com")
    _, second_headers = register_and_login(client, "second@example.com")
    profile = {
        "age": 30,
        "height_cm": "170.50",
        "weight_kg": "70.250",
        "activity_level": "moderately_active",
        "nutrition_goal": "general_health",
        "dietary_restrictions": ["  vegetarian  "],
        "allergies": ["peanut"],
    }
    created = client.put("/api/users/me/profile", json=profile, headers=first_headers)
    replaced = client.put(
        "/api/users/me/profile",
        json={"dietary_restrictions": ["vegan"], "allergies": []},
        headers=first_headers,
    )

    assert created.status_code == 200
    assert created.json()["user_id"] == first["id"]
    assert created.json()["dietary_restrictions"] == ["vegetarian"]
    assert replaced.status_code == 200
    assert replaced.json()["age"] is None
    assert client.get("/api/users/me/profile", headers=first_headers).json()["dietary_restrictions"] == ["vegan"]
    assert client.get("/api/users/me/profile", headers=second_headers).status_code == 404


def test_meals_are_owned_scoped_and_cannot_be_spoofed(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    food = create_test_food()
    database_session.add(food)
    database_session.flush()
    first, first_headers = register_and_login(client, "first@example.com")
    _, second_headers = register_and_login(client, "second@example.com")
    body = {"items": [{"food_id": food.id, "weight_grams": "100"}]}
    created = client.post("/api/meals", json=body, headers=first_headers)

    assert created.status_code == 201
    meal = database_session.get(Meal, created.json()["id"])
    assert meal is not None and meal.user_id == first["id"]
    assert client.get("/api/meals", headers=second_headers).json()["meals"] == []
    assert client.get(f"/api/meals/{meal.id}", headers=second_headers).status_code == 404
    assert client.post("/api/meals", json=body).status_code == 401
    assert client.post(
        "/api/meals", json={**body, "user_id": 999999}, headers=second_headers
    ).status_code == 422
    assert client.get(f"/api/meals/{meal.id}", headers=first_headers).status_code == 200


def test_profile_preserves_unknown_labels_and_allows_explicit_empty_label_lists(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)

    unknown = client.put("/api/users/me/profile", json={}, headers=headers)
    explicit_empty = client.put(
        "/api/users/me/profile",
        json={"dietary_restrictions": [], "allergies": []},
        headers=headers,
    )

    assert unknown.status_code == 200
    assert unknown.json()["dietary_restrictions"] is None
    assert unknown.json()["allergies"] is None
    assert explicit_empty.status_code == 200
    assert explicit_empty.json()["dietary_restrictions"] == []
    assert explicit_empty.json()["allergies"] == []


def test_profile_put_is_full_replacement_and_rejects_unauthorized_fields(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.put(
        "/api/users/me/profile",
        json={"age": 30, "dietary_restrictions": ["vegetarian"]},
        headers=headers,
    ).status_code == 200

    replaced = client.put("/api/users/me/profile", json={"weight_kg": "70.250"}, headers=headers)
    unsupported = client.put(
        "/api/users/me/profile",
        json={"medical_conditions": ["diabetes"], "email": "other@example.com"},
        headers=headers,
    )

    assert replaced.status_code == 200
    assert replaced.json()["age"] is None
    assert replaced.json()["dietary_restrictions"] is None
    assert replaced.json()["weight_kg"] == "70.250"
    assert unsupported.status_code == 422
    locations = {tuple(error["loc"]) for error in unsupported.json()["detail"]}
    assert ("body", "medical_conditions") in locations
    assert ("body", "email") in locations


def test_profile_rejects_invalid_physical_values_without_new_clinical_rules(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)

    assert client.put("/api/users/me/profile", json={"age": -1}, headers=headers).status_code == 422
    assert client.put("/api/users/me/profile", json={"height_cm": "0"}, headers=headers).status_code == 422
    assert client.put("/api/users/me/profile", json={"weight_kg": "0"}, headers=headers).status_code == 422


def test_authentication_configuration_failure_is_safe(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret_key", None)
    response = client.get("/api/users/me", headers={"Authorization": "Bearer any-token"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured."}
