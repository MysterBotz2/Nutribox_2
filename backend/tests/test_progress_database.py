from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.services.nutrient_calculator import NutrientCalculator
from conftest import register_and_login


def add_stored_meal(
    session: Session,
    *,
    user_id: int | None,
    recorded_at: datetime,
    calories: str = "100.000",
    protein: str = "10.000",
    carbohydrates: str = "20.000",
    fat: str = "3.000",
    fiber: str = "2.000",
) -> Meal:
    meal = Meal(
        user_id=user_id,
        recorded_at=recorded_at,
        total_calories=Decimal(calories),
        total_protein_g=Decimal(protein),
        total_carbohydrates_g=Decimal(carbohydrates),
        total_fat_g=Decimal(fat),
        total_fiber_g=Decimal(fiber),
    )
    session.add(meal)
    session.flush()
    return meal


def test_progress_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/progress/today").status_code == 401
    assert client.get("/api/progress/daily", params={"date": "2026-08-10"}).status_code == 401
    assert client.get("/api/progress/weekly", params={"week_start": "2026-08-10"}).status_code == 401
    assert client.get("/api/progress/summary").status_code == 401


def test_daily_progress_is_owned_snapshot_based_and_excludes_legacy(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    first, first_headers = register_and_login(client, "first@example.com")
    second, _ = register_and_login(client, "second@example.com")
    moment = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)
    add_stored_meal(database_session, user_id=first["id"], recorded_at=moment, calories="101.111")
    add_stored_meal(database_session, user_id=second["id"], recorded_at=moment, calories="999.000")
    add_stored_meal(database_session, user_id=None, recorded_at=moment, calories="888.000")

    response = client.get(
        "/api/progress/daily",
        params={"date": "2026-08-10", "timezone": "UTC"},
        headers=first_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-08-10",
        "meal_count": 1,
        "totals": {
            "calories": "101.111",
            "protein_g": "10.000",
            "carbohydrates_g": "20.000",
            "fat_g": "3.000",
            "fiber_g": "2.000",
        },
    }


def test_empty_daily_progress_has_decimal_zero_totals(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    response = client.get(
        "/api/progress/daily", params={"date": "2026-08-10"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["meal_count"] == 0
    assert response.json()["totals"] == {
        "calories": "0.000",
        "protein_g": "0.000",
        "carbohydrates_g": "0.000",
        "fat_g": "0.000",
        "fiber_g": "0.000",
    }


def test_daily_timezone_boundaries_and_exact_multiple_meal_sums(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 10, 15, 59, tzinfo=timezone.utc),
        calories="10.111",
    )
    add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 10, 16, 0, tzinfo=timezone.utc),
        calories="20.222",
    )
    add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 11, 2, 0, tzinfo=timezone.utc),
        calories="30.333",
    )

    august_tenth = client.get(
        "/api/progress/daily",
        params={"date": "2026-08-10", "timezone": "Asia/Manila"},
        headers=headers,
    )
    august_eleventh = client.get(
        "/api/progress/daily",
        params={"date": "2026-08-11", "timezone": "Asia/Manila"},
        headers=headers,
    )

    assert august_tenth.json()["meal_count"] == 1
    assert august_tenth.json()["totals"]["calories"] == "10.111"
    assert august_eleventh.json()["meal_count"] == 2
    assert august_eleventh.json()["totals"]["calories"] == "50.555"


def test_weekly_progress_is_monday_sunday_zero_filled_and_consistent(
    database_session: Session, client: TestClient, jwt_configuration: None
) -> None:
    user, headers = register_and_login(client)
    add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
        calories="100.000",
    )
    add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 16, 12, tzinfo=timezone.utc),
        calories="50.000",
    )
    response = client.get(
        "/api/progress/weekly",
        params={"week_start": "2026-08-10", "timezone": "UTC"},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["week_start"] == "2026-08-10"
    assert payload["week_end"] == "2026-08-16"
    assert len(payload["daily"]) == 7
    assert [point["date"] for point in payload["daily"]] == [
        "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14", "2026-08-15", "2026-08-16"
    ]
    assert payload["daily"][1]["totals"]["calories"] == "0.000"
    assert payload["meal_count"] == 2
    assert payload["totals"]["calories"] == "150.000"
    assert sum(Decimal(point["totals"]["calories"]) for point in payload["daily"]) == Decimal("150.000")
    assert client.get(
        "/api/progress/weekly", params={"week_start": "2026-08-11"}, headers=headers
    ).status_code == 422


def test_summary_bounds_average_all_calendar_days_and_today_clock(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.progress_service as progress_service

    monkeypatch.setattr(
        progress_service,
        "current_utc_datetime",
        lambda: datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
    )
    user, headers = register_and_login(client)
    add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 10, 8, tzinfo=timezone.utc),
        calories="90.000",
    )
    response = client.get(
        "/api/progress/summary", params={"days": 3, "timezone": "UTC"}, headers=headers
    )
    today = client.get("/api/progress/today", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["period_start"] == "2026-08-08"
    assert payload["period_end"] == "2026-08-10"
    assert payload["meal_count"] == payload["days_with_meals"] == 1
    assert payload["totals"]["calories"] == "90.000"
    assert payload["daily_average"]["calories"] == "30.000"
    assert len(payload["daily"]) == 3
    assert today.json()["date"] == "2026-08-10"
    assert client.get("/api/progress/summary", params={"days": 1}, headers=headers).status_code == 200
    assert client.get("/api/progress/summary", params={"days": 365}, headers=headers).status_code == 200
    assert client.get("/api/progress/summary", params={"days": 0}, headers=headers).status_code == 422
    assert client.get("/api/progress/summary", params={"days": 366}, headers=headers).status_code == 422


def test_invalid_timezone_and_food_changes_do_not_change_progress_snapshot(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    user, headers = register_and_login(client)
    food = Food(
        name="Progress Snapshot Food",
        category="test",
        calories_per_100g=Decimal("100.00"),
        protein_g_per_100g=Decimal("10.000"),
        carbohydrates_g_per_100g=Decimal("20.000"),
        fat_g_per_100g=Decimal("3.000"),
        fiber_g_per_100g=Decimal("2.000"),
        source_name="Synthetic test source",
        is_verified=False,
    )
    database_session.add(food)
    database_session.flush()
    meal = add_stored_meal(
        database_session,
        user_id=user["id"],
        recorded_at=datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
        calories="123.456",
    )
    database_session.add(
        MealItem(
            meal_id=meal.id,
            food_id=food.id,
            weight_grams=Decimal("100.000"),
            calculated_calories=Decimal("123.456"),
            calculated_protein_g=Decimal("10.000"),
            calculated_carbohydrates_g=Decimal("20.000"),
            calculated_fat_g=Decimal("3.000"),
            calculated_fiber_g=Decimal("2.000"),
            food_name_snapshot=food.name,
            food_normalized_name_snapshot=food.normalized_name,
        )
    )
    food.calories_per_100g = Decimal("999.00")
    database_session.flush()
    monkeypatch.setattr(
        NutrientCalculator,
        "calculate",
        lambda *_: (_ for _ in ()).throw(AssertionError("Progress must not calculate nutrients.")),
    )

    response = client.get(
        "/api/progress/daily", params={"date": "2026-08-10"}, headers=headers
    )
    invalid_timezone = client.get(
        "/api/progress/daily", params={"date": "2026-08-10", "timezone": "Not/AZone"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["totals"]["calories"] == "123.456"
    assert invalid_timezone.status_code == 422
