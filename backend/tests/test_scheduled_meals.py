from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meal import Meal
from app.models.nutrition_target import NutritionTarget
from app.models.scheduled_meal import ScheduledMeal
from app.models.user import User
from conftest import register_and_login


def schedule_payload(**overrides: object) -> dict[str, object]:
    return {
        "scheduled_for": "2026-08-24T12:30:00+08:00",
        "title": "Lunch",
        "notes": "Bring a packed meal.",
        **overrides,
    }


def create_schedule(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post("/api/scheduled-meals", json=schedule_payload(**overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_scheduled_meal_creation_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/scheduled-meals", json=schedule_payload()).status_code == 401
    assert client.get("/api/scheduled-meals").status_code == 401


def test_scheduled_meal_is_created_for_token_owner_and_retrievable(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    created = create_schedule(client, headers)

    stored = database_session.get(ScheduledMeal, created["id"])
    fetched = client.get(f"/api/scheduled-meals/{created['id']}", headers=headers)

    assert stored is not None and stored.user_id == user["id"]
    assert created["title"] == "Lunch"
    assert created["notes"] == "Bring a packed meal."
    assert created["scheduled_for"] == "2026-08-24T04:30:00Z"
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_scheduled_meal_write_validation_and_unknown_fields_are_rejected(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    cases = [
        {},
        schedule_payload(scheduled_for="not-a-timestamp"),
        schedule_payload(scheduled_for="2026-08-24T12:30:00"),
        schedule_payload(title=""),
        schedule_payload(title="x" * 161),
        schedule_payload(notes="x" * 1001),
        schedule_payload(user_id=999999),
        schedule_payload(planned_calories="900.000"),
        schedule_payload(medical_conditions=["diabetes"]),
        schedule_payload(ai_instruction="plan this"),
    ]

    for payload in cases:
        assert client.post("/api/scheduled-meals", json=payload, headers=headers).status_code == 422


def test_scheduled_meal_owner_isolation_for_read_update_and_delete(
    client: TestClient, jwt_configuration: None
) -> None:
    _, first_headers = register_and_login(client, "first@example.com")
    _, second_headers = register_and_login(client, "second@example.com")
    created = create_schedule(client, first_headers)
    schedule_id = created["id"]

    assert client.get(f"/api/scheduled-meals/{schedule_id}", headers=second_headers).status_code == 404
    assert client.put(
        f"/api/scheduled-meals/{schedule_id}", json=schedule_payload(title="Changed"), headers=second_headers
    ).status_code == 404
    assert client.delete(f"/api/scheduled-meals/{schedule_id}", headers=second_headers).status_code == 404

    updated = client.put(
        f"/api/scheduled-meals/{schedule_id}",
        json=schedule_payload(title="Updated lunch", notes=None),
        headers=first_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated lunch"
    assert updated.json()["notes"] is None
    assert client.delete(f"/api/scheduled-meals/{schedule_id}", headers=first_headers).status_code == 204
    assert client.get(f"/api/scheduled-meals/{schedule_id}", headers=first_headers).status_code == 404


def test_scheduled_meal_list_is_owner_scoped_ordered_paginated_and_window_filtered(
    client: TestClient, jwt_configuration: None
) -> None:
    _, first_headers = register_and_login(client, "first@example.com")
    _, second_headers = register_and_login(client, "second@example.com")
    later = create_schedule(client, first_headers, scheduled_for="2026-08-25T10:00:00Z", title="Later")
    first = create_schedule(client, first_headers, scheduled_for="2026-08-24T10:00:00Z", title="First")
    same_time = create_schedule(client, first_headers, scheduled_for="2026-08-24T10:00:00Z", title="Same time")
    create_schedule(client, second_headers, scheduled_for="2026-08-24T10:00:00Z", title="Other user")

    listed = client.get("/api/scheduled-meals", headers=first_headers)
    filtered_from = client.get(
        "/api/scheduled-meals",
        params={"scheduled_from": "2026-08-24T10:00:00Z"},
        headers=first_headers,
    )
    filtered_to = client.get(
        "/api/scheduled-meals",
        params={"scheduled_to": "2026-08-24T10:00:00Z"},
        headers=first_headers,
    )
    combined = client.get(
        "/api/scheduled-meals",
        params={
            "scheduled_from": "2026-08-24T10:00:00Z",
            "scheduled_to": "2026-08-24T10:00:00Z",
            "limit": 1,
            "offset": 1,
        },
        headers=first_headers,
    )

    assert [item["id"] for item in listed.json()["scheduled_meals"]] == [first["id"], same_time["id"], later["id"]]
    assert [item["id"] for item in filtered_from.json()["scheduled_meals"]] == [first["id"], same_time["id"], later["id"]]
    assert [item["id"] for item in filtered_to.json()["scheduled_meals"]] == [first["id"], same_time["id"]]
    assert [item["id"] for item in combined.json()["scheduled_meals"]] == [same_time["id"]]
    assert combined.json()["limit"] == 1
    assert combined.json()["offset"] == 1
    assert client.get(
        "/api/scheduled-meals", params={"scheduled_from": "2026-08-26T00:00:00Z"}, headers=first_headers
    ).json()["scheduled_meals"] == []


def test_scheduled_meal_window_validation_and_past_entries(client: TestClient, jwt_configuration: None) -> None:
    _, headers = register_and_login(client)
    past = create_schedule(client, headers, scheduled_for="2020-01-01T09:00:00Z")

    assert past["scheduled_for"] == "2020-01-01T09:00:00Z"
    assert client.get(
        "/api/scheduled-meals",
        params={"scheduled_from": "2026-08-25T00:00:00Z", "scheduled_to": "2026-08-24T00:00:00Z"},
        headers=headers,
    ).status_code == 422
    assert client.get(
        "/api/scheduled-meals", params={"scheduled_from": "not-a-timestamp"}, headers=headers
    ).status_code == 422
    assert client.get(
        "/api/scheduled-meals", params={"scheduled_from": "2026-08-24T00:00:00"}, headers=headers
    ).status_code == 422


def test_scheduled_meal_has_no_actual_meal_target_or_sensitive_side_effects(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.food_recognition_selector as recognition_selector
    import app.services.nutrition_coach_selector as coach_selector

    user, headers = register_and_login(client)
    database_session.add(
        NutritionTarget(
            user_id=user["id"],
            calories=100,
            source_type="manual",
        )
    )
    database_session.flush()
    monkeypatch.setattr(
        recognition_selector,
        "get_food_recognition_provider",
        lambda: (_ for _ in ()).throw(AssertionError("Schedule CRUD must not use food recognition.")),
    )
    monkeypatch.setattr(
        coach_selector,
        "get_nutrition_coach_provider",
        lambda: (_ for _ in ()).throw(AssertionError("Schedule CRUD must not use Coach.")),
    )

    created = create_schedule(client, headers)
    client.put(
        f"/api/scheduled-meals/{created['id']}", json=schedule_payload(title="Changed"), headers=headers
    )

    assert database_session.query(Meal).filter_by(user_id=user["id"]).count() == 0
    assert database_session.query(NutritionTarget).filter_by(user_id=user["id"]).one().calories == 100


def test_deleting_user_cascades_scheduled_meals(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    created = create_schedule(client, headers)

    database_session.delete(database_session.get(User, user["id"]))
    database_session.flush()

    assert database_session.get(ScheduledMeal, created["id"]) is None


def test_scheduled_meal_model_uses_timezone_aware_timestamp() -> None:
    assert ScheduledMeal.scheduled_for.type.timezone is True
    assert datetime.now(timezone.utc).tzinfo is timezone.utc
