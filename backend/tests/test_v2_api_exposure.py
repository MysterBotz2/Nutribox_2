from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.food import Food


def make_food(name: str, **values: Decimal | str | None) -> Food:
    food = Food(
        name=name,
        category="test",
        calories_per_100g=Decimal("100.00"),
        protein_g_per_100g=Decimal("10.000"),
        carbohydrates_g_per_100g=Decimal("20.000"),
        fat_g_per_100g=Decimal("3.000"),
        fiber_g_per_100g=Decimal("2.000"),
        source_name="Test reference",
        source_reference="test:1",
        source_type="local_database",
        is_verified=True,
    )
    for field, value in values.items():
        setattr(food, field, value)
    return food


def test_food_and_calculation_apis_expose_v2_values_nulls_zeroes_and_source_category(
    database_session: Session, client: TestClient
) -> None:
    food = make_food(
        "Extended Food",
        saturated_fat_g_per_100g=Decimal("1.000"),
        sugars_g_per_100g=Decimal("0.000"),
        sodium_mg_per_100g=Decimal("200.000"),
        omega_3_g_per_100g=None,
        vitamin_b12_mcg_per_100g=Decimal("0.500"),
    )
    database_session.add(food)
    database_session.flush()

    food_response = client.get(f"/api/nutrition/{food.id}")
    calculation_response = client.post(
        "/api/nutrition/calculate", json={"food_id": food.id, "weight_grams": "150"}
    )

    assert food_response.status_code == 200
    reference = food_response.json()
    assert reference["nutrition_per_100g"]["saturated_fat_g"] == "1.000"
    assert reference["nutrition_per_100g"]["sugars_g"] == "0.000"
    assert reference["nutrition_per_100g"]["omega_3_g"] is None
    assert reference["nutrition_per_100g"]["vitamin_b12_mcg"] == "0.500"
    assert reference["source"]["category"] == "local_database"

    assert calculation_response.status_code == 200
    nutrition = calculation_response.json()["nutrition"]
    assert nutrition["calories"] == "150.000"
    assert nutrition["saturated_fat_g"] == "1.500"
    assert nutrition["sugars_g"] == "0.000"
    assert nutrition["sodium_mg"] == "300.000"
    assert nutrition["omega_3_g"] is None
    assert nutrition["vitamin_b12_mcg"] == "0.750"


def test_meal_detail_exposes_immutable_v2_snapshots_and_truthful_additional_totals(
    database_session: Session, client: TestClient, auth_headers: dict[str, str]
) -> None:
    known = make_food(
        "Known V2 Food",
        saturated_fat_g_per_100g=Decimal("1.000"),
        sugars_g_per_100g=Decimal("0.000"),
        sodium_mg_per_100g=Decimal("200.000"),
        vitamin_b12_mcg_per_100g=Decimal("0.500"),
    )
    unknown = make_food("Unknown V2 Food")
    unknown.source_type = "AI_estimate"
    unknown.is_verified = False
    database_session.add_all([known, unknown])
    database_session.flush()

    created = client.post(
        "/api/meals",
        json={"items": [
            {"food_id": known.id, "weight_grams": "100"},
            {"food_id": unknown.id, "weight_grams": "100"},
        ]},
        headers=auth_headers,
    )
    detail = client.get(f"/api/meals/{created.json()['id']}", headers=auth_headers)

    assert created.status_code == 201
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["totals"]["calories"] == "200.000"
    assert payload["items"][0]["nutrition"]["sodium_mg"] == "200.000"
    assert payload["items"][1]["nutrition"]["sodium_mg"] is None
    assert payload["items"][0]["nutrition_source"]["category"] == "local_database"
    assert payload["items"][1]["nutrition_source"]["category"] == "AI_estimate"
    assert payload["items"][1]["nutrition_source"]["is_estimated"] is True
    assert payload["additional_totals"]["sodium_mg"] is None
    assert payload["additional_totals"]["sugars_g"] is None


def test_meal_detail_additional_total_preserves_explicit_zero(
    database_session: Session, client: TestClient, auth_headers: dict[str, str]
) -> None:
    food = make_food(
        "Zero Sugar Food",
        saturated_fat_g_per_100g=Decimal("0.000"),
        sugars_g_per_100g=Decimal("0.000"),
        sodium_mg_per_100g=Decimal("0.000"),
        cholesterol_mg_per_100g=Decimal("0.000"),
    )
    database_session.add(food)
    database_session.flush()

    response = client.post(
        "/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "150"}]}, headers=auth_headers
    )

    assert response.status_code == 201
    assert response.json()["additional_totals"]["sugars_g"] == "0.000"
    assert response.json()["additional_totals"]["sodium_mg"] == "0.000"


def test_meal_list_remains_compact_while_detail_has_v2_snapshots(
    database_session: Session, client: TestClient, auth_headers: dict[str, str]
) -> None:
    food = make_food("List Compatibility Food", sodium_mg_per_100g=Decimal("1.000"))
    database_session.add(food)
    database_session.flush()
    client.post(
        "/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "100"}]}, headers=auth_headers
    )

    listed = client.get("/api/meals", headers=auth_headers)

    assert listed.status_code == 200
    assert "sodium_mg" not in listed.json()["meals"][0]["items"][0]["nutrition"]
    assert "additional_totals" not in listed.json()["meals"][0]
