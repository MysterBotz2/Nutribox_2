from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.nutrition_target import NutritionTarget
from app.models.user import User
from app.services.nutrient_calculator import NutrientCalculator
from conftest import register_and_login


def target_payload(**overrides: object) -> dict[str, object]:
    return {
        "calories": "100.000",
        "protein_g": "50.000",
        "carbohydrates_g": None,
        "fat_g": None,
        "fiber_g": None,
        "source_type": "researcher_assigned",
        "source_reference": "TEST-PROTOCOL",
        "notes": "Test target only.",
        **overrides,
    }


def add_stored_meal(session: Session, user_id: int, calories: str) -> Meal:
    meal = Meal(
        user_id=user_id,
        recorded_at=datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
        total_calories=Decimal(calories),
        total_protein_g=Decimal("20.000"),
        total_carbohydrates_g=Decimal("30.000"),
        total_fat_g=Decimal("4.000"),
        total_fiber_g=Decimal("5.000"),
    )
    session.add(meal)
    session.flush()
    return meal


def test_targets_require_authentication(client: TestClient) -> None:
    assert client.get("/api/users/me/targets").status_code == 401
    assert client.put("/api/users/me/targets", json=target_payload()).status_code == 401
    assert client.get("/api/progress/target-status").status_code == 401


def test_targets_create_retrieve_update_and_preserve_decimal_precision(
    client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    created = client.put(
        "/api/users/me/targets",
        json=target_payload(calories="123.456", protein_g=None, source_type="manual"),
        headers=headers,
    )
    fetched = client.get("/api/users/me/targets", headers=headers)
    updated = client.put(
        "/api/users/me/targets",
        json=target_payload(calories=None, fiber_g="30.123", notes=None),
        headers=headers,
    )

    assert created.status_code == 200
    assert created.json()["user_id"] == user["id"]
    assert created.json()["calories"] == "123.456"
    assert created.json()["protein_g"] is None
    assert created.json()["source_type"] == "manual"
    assert fetched.json()["source_reference"] == "TEST-PROTOCOL"
    assert updated.status_code == 200
    assert updated.json()["calories"] is None
    assert updated.json()["fiber_g"] == "30.123"
    assert updated.json()["notes"] is None
    assert client.get("/api/users/me/targets", headers=headers).json()["id"] == created.json()["id"]


def test_targets_are_owned_and_client_cannot_spoof_user(
    client: TestClient, jwt_configuration: None
) -> None:
    _, first_headers = register_and_login(client, "first@example.com")
    _, second_headers = register_and_login(client, "second@example.com")
    assert client.put("/api/users/me/targets", json=target_payload(), headers=first_headers).status_code == 200

    assert client.get("/api/users/me/targets", headers=second_headers).status_code == 404
    assert client.put(
        "/api/users/me/targets",
        json=target_payload(user_id=999999),
        headers=second_headers,
    ).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("calories", "0"),
        ("calories", "-1"),
        ("calories", "NaN"),
        ("calories", "Infinity"),
        ("protein_g", "10000.001"),
    ],
)
def test_target_numeric_validation_rejects_invalid_values(
    client: TestClient, jwt_configuration: None, field: str, value: str
) -> None:
    _, headers = register_and_login(client)
    assert client.put(
        "/api/users/me/targets", json=target_payload(**{field: value}), headers=headers
    ).status_code == 422


def test_target_provenance_and_at_least_one_value_are_validated(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    no_values = target_payload(calories=None, protein_g=None)
    invalid_source = target_payload(source_type="validated_formula")

    assert client.put("/api/users/me/targets", json=no_values, headers=headers).status_code == 422
    assert client.put("/api/users/me/targets", json=invalid_source, headers=headers).status_code == 422


def test_deleting_user_cascades_targets(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    assert client.put("/api/users/me/targets", json=target_payload(), headers=headers).status_code == 200
    database_session.delete(database_session.get(User, user["id"]))
    database_session.flush()

    assert database_session.query(NutritionTarget).filter_by(user_id=user["id"]).one_or_none() is None


def test_target_status_uses_stored_meals_current_user_and_negative_remaining(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.progress_service as progress_service

    monkeypatch.setattr(
        progress_service,
        "current_utc_datetime",
        lambda: datetime(2026, 8, 10, 15, tzinfo=timezone.utc),
    )
    first, first_headers = register_and_login(client, "first@example.com")
    second, second_headers = register_and_login(client, "second@example.com")
    assert client.put(
        "/api/users/me/targets",
        json=target_payload(calories="100.000", protein_g=None),
        headers=first_headers,
    ).status_code == 200
    assert client.put(
        "/api/users/me/targets",
        json=target_payload(calories="999.000"),
        headers=second_headers,
    ).status_code == 200
    add_stored_meal(database_session, first["id"], "150.000")
    add_stored_meal(database_session, second["id"], "999.000")
    monkeypatch.setattr(
        NutrientCalculator,
        "calculate",
        lambda *_: (_ for _ in ()).throw(AssertionError("Target status must not calculate nutrients.")),
    )

    response = client.get("/api/progress/target-status", headers=first_headers)
    payload = response.json()

    assert response.status_code == 200
    assert payload["consumed"]["calories"] == "150.000"
    assert payload["targets"]["calories"] == "100.000"
    assert payload["remaining"]["calories"] == "-50.000"
    assert payload["percent_of_target"]["calories"] == "150.000"
    assert payload["targets"]["protein_g"] is None
    assert payload["remaining"]["protein_g"] is None
    assert payload["percent_of_target"]["protein_g"] is None


def test_target_status_has_null_comparison_when_targets_are_missing(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.progress_service as progress_service

    monkeypatch.setattr(
        progress_service,
        "current_utc_datetime",
        lambda: datetime(2026, 8, 10, 15, tzinfo=timezone.utc),
    )
    user, headers = register_and_login(client)
    add_stored_meal(database_session, user["id"], "100.000")
    response = client.get("/api/progress/target-status", headers=headers)

    assert response.status_code == 200
    assert response.json()["targets"] is None
    assert response.json()["remaining"] is None
    assert response.json()["percent_of_target"] is None
