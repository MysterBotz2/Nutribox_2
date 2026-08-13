from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.food import Food
from app.routers.nutrition import get_nutrition_service
from app.schemas.nutrition import NutritionPer100g
from app.services.nutrient_calculator import NutrientCalculator
from app.services.nutrition_service import NutritionService


@pytest.fixture
def reference_nutrition() -> NutritionPer100g:
    return NutritionPer100g(
        calories=Decimal("150.00"),
        protein_g=Decimal("20.000"),
        carbohydrates_g=Decimal("30.000"),
        fat_g=Decimal("10.000"),
        fiber_g=Decimal("5.000"),
    )


def test_calculator_at_100g_returns_reference_values(
    reference_nutrition: NutritionPer100g,
) -> None:
    result = NutrientCalculator().calculate(reference_nutrition, Decimal("100"))

    assert {key: result.model_dump()[key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": Decimal("150.000"),
        "protein_g": Decimal("20.000"),
        "carbohydrates_g": Decimal("30.000"),
        "fat_g": Decimal("10.000"),
        "fiber_g": Decimal("5.000"),
    }


def test_calculator_at_50g_returns_half_values(reference_nutrition: NutritionPer100g) -> None:
    result = NutrientCalculator().calculate(reference_nutrition, Decimal("50"))

    assert {key: result.model_dump()[key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": Decimal("75.000"),
        "protein_g": Decimal("10.000"),
        "carbohydrates_g": Decimal("15.000"),
        "fat_g": Decimal("5.000"),
        "fiber_g": Decimal("2.500"),
    }


def test_calculator_at_200g_returns_double_values(reference_nutrition: NutritionPer100g) -> None:
    result = NutrientCalculator().calculate(reference_nutrition, Decimal("200"))

    assert result.calories == Decimal("300.000")
    assert result.protein_g == Decimal("40.000")
    assert result.carbohydrates_g == Decimal("60.000")
    assert result.fat_g == Decimal("20.000")
    assert result.fiber_g == Decimal("10.000")


def test_calculator_at_zero_grams_returns_zero(reference_nutrition: NutritionPer100g) -> None:
    result = NutrientCalculator().calculate(reference_nutrition, Decimal("0"))

    assert {key: result.model_dump()[key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": Decimal("0.000"),
        "protein_g": Decimal("0.000"),
        "carbohydrates_g": Decimal("0.000"),
        "fat_g": Decimal("0.000"),
        "fiber_g": Decimal("0.000"),
    }


def test_calculator_handles_fractional_weight_deterministically() -> None:
    reference = NutritionPer100g(
        calories=Decimal("100.12"),
        protein_g=Decimal("10.123"),
        carbohydrates_g=Decimal("20.456"),
        fat_g=Decimal("3.789"),
        fiber_g=Decimal("2.345"),
    )

    result = NutrientCalculator().calculate(reference, Decimal("125.5"))

    assert {key: result.model_dump()[key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": Decimal("125.651"),
        "protein_g": Decimal("12.704"),
        "carbohydrates_g": Decimal("25.672"),
        "fat_g": Decimal("4.755"),
        "fiber_g": Decimal("2.943"),
    }


def test_calculator_uses_round_half_up() -> None:
    reference = NutritionPer100g(
        calories=Decimal("1.2345"),
        protein_g=Decimal("1.2345"),
        carbohydrates_g=Decimal("1.2345"),
        fat_g=Decimal("1.2345"),
        fiber_g=Decimal("1.2345"),
    )

    result = NutrientCalculator().calculate(reference, Decimal("100"))

    assert result.calories == Decimal("1.235")


@pytest.mark.parametrize(
    "weight_grams",
    ["not-a-decimal", Decimal("-0.001"), Decimal("5000.001"), Decimal("NaN"), Decimal("Infinity")],
)
def test_calculator_rejects_invalid_weights(
    reference_nutrition: NutritionPer100g, weight_grams: Decimal | str
) -> None:
    with pytest.raises(ValueError):
        NutrientCalculator().calculate(reference_nutrition, weight_grams)  # type: ignore[arg-type]


class StubFoodRepository:
    """Minimal in-memory repository used to test API wiring without a database."""

    def __init__(self, food: Food | None) -> None:
        self._food = food

    def get_by_id(self, food_id: int) -> Food | None:
        if self._food is not None and food_id == self._food.id:
            return self._food
        return None


def create_api_test_food() -> Food:
    return Food(
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


def test_calculation_endpoint_returns_nested_portion_response() -> None:
    service = NutritionService(StubFoodRepository(create_api_test_food()))  # type: ignore[arg-type]
    app.dependency_overrides[get_nutrition_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/nutrition/calculate",
            json={"food_id": 1, "weight_grams": "180"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["food"] == {"id": 1, "name": "Test Food"}
    assert payload["weight_grams"] == "180"
    assert {key: payload["nutrition"][key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": "180.000", "protein_g": "18.000", "carbohydrates_g": "36.000", "fat_g": "5.400", "fiber_g": "3.600",
    }


def test_calculation_endpoint_returns_404_for_unknown_food() -> None:
    service = NutritionService(StubFoodRepository(None))  # type: ignore[arg-type]
    app.dependency_overrides[get_nutrition_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/api/nutrition/calculate",
            json={"food_id": 1, "weight_grams": "180"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Food record was not found."}
