from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.food import Food
from app.models.meal import Meal
from app.models.meal_analysis_session import MealAnalysisSession
from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
)
from conftest import register_and_login


def _food() -> Food:
    return Food(
        name="Paired leftover scan food",
        normalized_name="paired leftover scan food",
        category="test",
        calories_per_100g=Decimal("100"),
        protein_g_per_100g=Decimal("10"),
        carbohydrates_g_per_100g=Decimal("20"),
        fat_g_per_100g=Decimal("3"),
        fiber_g_per_100g=Decimal("2"),
        saturated_fat_g_per_100g=Decimal("1"),
        sugars_g_per_100g=Decimal("2"),
        sodium_mg_per_100g=Decimal("10"),
        cholesterol_mg_per_100g=None,
        omega_3_g_per_100g=Decimal(".1"),
        omega_6_g_per_100g=Decimal(".2"),
        calcium_mg_per_100g=Decimal("5"),
        potassium_mg_per_100g=Decimal("15"),
        zinc_mg_per_100g=Decimal(".5"),
        iron_mg_per_100g=Decimal(".7"),
        magnesium_mg_per_100g=Decimal("8"),
        phosphorus_mg_per_100g=Decimal("20"),
        vitamin_b6_mg_per_100g=Decimal(".4"),
        niacin_mg_per_100g=Decimal("2"),
        vitamin_a_mcg_rae_per_100g=None,
        vitamin_b12_mcg_per_100g=None,
        vitamin_c_mg_per_100g=Decimal("3"),
        vitamin_d_mcg_per_100g=None,
        folate_mcg_dfe_per_100g=Decimal("4"),
        source_name="test",
        source_type="local_database",
        source_reference="test:leftover-scan",
        is_verified=True,
    )


def _measured_meal(
    client: TestClient, database_session: Session, headers: dict[str, str], food: Food
) -> dict:
    response = client.post(
        "/api/meals",
        json={"items": [{"food_id": food.id, "weight_grams": "100"}]},
        headers=headers,
    )
    assert response.status_code == 201
    meal = database_session.get(Meal, response.json()["id"])
    assert meal is not None
    meal.measured_weight_grams = Decimal("100")
    database_session.flush()
    return response.json()


def _nutrition(*, calories: str = "50") -> dict[str, str | None]:
    return {
        "calories": calories,
        "protein_g": "5",
        "carbohydrates_g": "10",
        "fat_g": "1.5",
        "fiber_g": "1",
        "saturated_fat_g": ".5",
        "sugars_g": "1",
        "sodium_mg": "5",
        "cholesterol_mg": None,
        "omega_3_g": ".05",
        "omega_6_g": ".1",
        "calcium_mg": "2.5",
        "potassium_mg": "7.5",
        "zinc_mg": ".25",
        "iron_mg": ".35",
        "magnesium_mg": "4",
        "phosphorus_mg": "10",
        "vitamin_b6_mg": ".2",
        "niacin_mg": "1",
        "vitamin_a_mcg_rae": None,
        "vitamin_b12_mcg": None,
        "vitamin_c_mg": "1.5",
        "vitamin_d_mcg": None,
        "folate_mcg_dfe": "2",
    }


def _completed_session(
    database_session: Session, *, user_id: int, weight: str = "50", calories: str = "50", status: str = "calculated"
) -> MealAnalysisSession:
    state = MealAnalysisSessionState(
        measured_weight_grams=Decimal(weight),
        components=[
            MealAnalysisSessionComponent(
                recognized_name="Paired leftover scan food",
                raw_estimated_proportion=Decimal("1"),
                normalized_proportion=Decimal("1"),
                estimated_weight_grams=Decimal(weight),
                resolution_status=ComponentResolutionStatus.RESOLVED,
                resolved_reference="food:1",
                nutrition_source="local_database",
                nutrition=_nutrition(calories=calories),
            )
        ],
    )
    item = MealAnalysisSession(
        user_id=user_id,
        state=state.model_dump(mode="json"),
        status=status,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
    )
    database_session.add(item)
    database_session.flush()
    return item


def _pair_device(client: TestClient, owner_headers: dict[str, str], monkeypatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "device_pairing_secret", "test-pairing-secret")
    started = client.post("/api/device-pairing/start", json={"device_name": "Leftover Test Pi"})
    assert started.status_code == 201
    assert client.post(
        "/api/users/me/devices/pair",
        json={"pairing_code": started.json()["pairing_code"]},
        headers=owner_headers,
    ).status_code == 201
    return {"X-Device-Token": started.json()["device_token"]}


def test_bearer_leftover_scan_persists_expanded_snapshots_and_consumes_session(
    client: TestClient, database_session: Session, jwt_configuration: None
) -> None:
    food = _food()
    database_session.add(food)
    database_session.flush()
    owner, headers = register_and_login(client, "leftover-scan-owner@example.com")
    meal = _measured_meal(client, database_session, headers, food)
    analysis = _completed_session(database_session, user_id=owner["id"])

    response = client.post(
        f"/api/meals/{meal['id']}/leftover-scans",
        json={"analysis_session_id": analysis.id},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["meal_id"] == meal["id"]
    assert body["analysis_session_id"] == analysis.id
    assert Decimal(body["original_weight_grams"]) == Decimal("100.000")
    assert Decimal(body["remaining_weight_grams"]) == Decimal("50.000")
    assert Decimal(body["consumed_weight_grams"]) == Decimal("50.000")
    assert Decimal(body["consumed_portion_percentage"]) == Decimal("50.000")
    assert body["remaining_nutrition"]["phosphorus_mg"] == "10"
    assert body["estimated_consumed_nutrition"]["vitamin_b6_mg"] == "0.200"
    assert body["estimated_consumed_nutrition"]["niacin_mg"] == "1.000"
    assert body["estimated_consumed_nutrition"]["energy_kj"] == "209.200"
    assert body["estimated_consumed_nutrition"]["cholesterol_mg"] is None
    assert body["comparison_warnings"] == []
    assert database_session.get(MealAnalysisSession, analysis.id).consumed_at is not None
    unchanged = client.get(f"/api/meals/{meal['id']}", headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["totals"] == meal["totals"]


def test_leftover_scan_owner_isolation_completed_state_and_weight_invariants(
    client: TestClient, database_session: Session, jwt_configuration: None
) -> None:
    food = _food()
    database_session.add(food)
    database_session.flush()
    owner, owner_headers = register_and_login(client, "leftover-scan-owner-2@example.com")
    other, other_headers = register_and_login(client, "leftover-scan-other@example.com")
    meal = _measured_meal(client, database_session, owner_headers, food)
    owner_session = _completed_session(database_session, user_id=owner["id"])
    other_session = _completed_session(database_session, user_id=other["id"])
    incomplete = _completed_session(database_session, user_id=owner["id"], status="requires_food_selection")
    too_heavy = _completed_session(database_session, user_id=owner["id"], weight="101")

    assert client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": other_session.id}, headers=owner_headers
    ).status_code == 404
    assert client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": incomplete.id}, headers=owner_headers
    ).status_code == 422
    assert client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": too_heavy.id}, headers=owner_headers
    ).status_code == 409
    assert client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": owner_session.id}, headers=other_headers
    ).status_code == 404


def test_leftover_scan_clamps_negative_nutrients_and_prevents_duplicate_consumption(
    client: TestClient, database_session: Session, jwt_configuration: None
) -> None:
    food = _food()
    database_session.add(food)
    database_session.flush()
    owner, headers = register_and_login(client, "leftover-scan-clamp@example.com")
    meal = _measured_meal(client, database_session, headers, food)
    analysis = _completed_session(database_session, user_id=owner["id"], calories="120")

    created = client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": analysis.id}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["estimated_consumed_nutrition"]["calories"] == "0"
    assert {warning["nutrient"] for warning in created.json()["comparison_warnings"]} >= {"calories"}
    duplicate = client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": analysis.id}, headers=headers
    )
    assert duplicate.status_code == 409


def test_paired_device_can_list_read_and_create_owner_leftover_scan(
    client: TestClient, database_session: Session, jwt_configuration: None, monkeypatch
) -> None:
    food = _food()
    database_session.add(food)
    database_session.flush()
    owner, owner_headers = register_and_login(client, "leftover-device-owner@example.com")
    meal = _measured_meal(client, database_session, owner_headers, food)
    device_headers = _pair_device(client, owner_headers, monkeypatch)
    assert client.get("/api/meals", headers=device_headers).status_code == 200
    assert client.get(f"/api/meals/{meal['id']}", headers=device_headers).status_code == 200
    analysis = _completed_session(database_session, user_id=owner["id"])
    assert client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": analysis.id}, headers=device_headers
    ).status_code == 201
    device_id = client.get("/api/users/me/devices", headers=owner_headers).json()["devices"][0]["id"]
    assert client.delete(f"/api/users/me/devices/{device_id}", headers=owner_headers).status_code == 204
    assert client.get("/api/meals", headers=device_headers).status_code == 401
    assert client.post(
        f"/api/meals/{meal['id']}/leftover-scans", json={"analysis_session_id": analysis.id}, headers={**owner_headers, **device_headers}
    ).status_code == 400
