from decimal import Decimal

from app.models.food import Food, normalize_food_name
from app.schemas.nutrition import FoodResponse


def test_normalize_food_name_trims_casefolds_and_collapses_whitespace() -> None:
    assert normalize_food_name("  White   Rice  ") == "white rice"


def test_food_response_serializes_decimal_values_consistently() -> None:
    food = Food(
        id=1,
        name="Test Food",
        normalized_name="test food",
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

    response = FoodResponse.from_food(food)

    payload = response.model_dump(mode="json")
    assert payload["id"] == 1
    assert payload["name"] == "Test Food"
    assert payload["nutrition_per_100g"]["saturated_fat_g"] is None
    assert {key: payload["nutrition_per_100g"][key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": "100.00", "protein_g": "10.000", "carbohydrates_g": "20.000", "fat_g": "3.000", "fiber_g": "2.000",
    }
    assert payload["source"] == {"name": "Synthetic test source", "reference": "test-only", "verified": False, "category": None}
