from decimal import Decimal
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models.food import Food, normalize_food_name
from app.routers.meals import get_meal_analysis_service
from app.schemas.nutrition import NutritionPer100g
from app.services.food_recognition_provider import (
    FoodRecognitionProvider,
    FoodRecognitionResult,
)
from app.services.meal_analysis_service import MealAnalysisService
from app.services.nutrient_calculator import NutrientCalculator
from app.services.nutrition_service import NutritionService
from app.services.usda_food_reference_service import UsdaResolution


class StubFoodRecognitionProvider(FoodRecognitionProvider):
    def __init__(self, food_names: tuple[str, ...], source: str = "simulated") -> None:
        self._result = FoodRecognitionResult(food_names=food_names, source=source)

    def recognize_food(
        self, *, image_bytes: bytes, content_type: str
    ) -> FoodRecognitionResult:
        return self._result


class StubFoodRepository:
    def __init__(self, food: Food | None) -> None:
        self._food = food

    def get_by_normalized_name(self, normalized_name: str) -> Food | None:
        if self._food is None:
            return None
        if normalized_name == self._food.normalized_name:
            return self._food
        return None


class FailingCalculator(NutrientCalculator):
    def calculate(
        self, nutrition_per_100g: NutritionPer100g, weight_grams: Decimal
    ):
        raise AssertionError("Calculator must not run for this analysis outcome.")


def create_test_food() -> Food:
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


def create_service(
    recognized_names: tuple[str, ...],
    food: Food | None = None,
    calculator: NutrientCalculator | None = None,
) -> MealAnalysisService:
    return MealAnalysisService(
        StubFoodRecognitionProvider(recognized_names),
        NutritionService(StubFoodRepository(food)),  # type: ignore[arg-type]
        calculator,
    )


def test_single_recognized_food_with_reference_is_calculated() -> None:
    result = create_service((" Test   Food ",), create_test_food()).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("180")
    )

    assert result.status == "calculated"
    assert result.recognition_source == "simulated"
    assert result.weight_source == "manual"
    assert result.food.name == "Test Food"
    assert {key: result.nutrition.model_dump()[key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": Decimal("180.000"),
        "protein_g": Decimal("18.000"),
        "carbohydrates_g": Decimal("36.000"),
        "fat_g": Decimal("5.400"),
        "fiber_g": Decimal("3.600"),
    }


def test_local_food_match_does_not_invoke_usda_fallback() -> None:
    class NoUsdaFallback:
        def resolve(self, _: str):
            raise AssertionError("USDA must not be called when local nutrition exists.")

    service = MealAnalysisService(
        StubFoodRecognitionProvider(("Test Food",)),
        NutritionService(StubFoodRepository(create_test_food())),  # type: ignore[arg-type]
        usda_food_reference_service=NoUsdaFallback(),  # type: ignore[arg-type]
    )
    assert service.analyze(image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("100")).status == "calculated"


def test_usda_fallback_uses_existing_calculator_for_measured_weight() -> None:
    class UsdaFallback:
        def __init__(self) -> None:
            self.called = False

        def resolve(self, _: str) -> UsdaResolution:
            self.called = True
            return UsdaResolution(food=create_test_food())

    fallback = UsdaFallback()
    service = MealAnalysisService(
        StubFoodRecognitionProvider(("Uncached food",)),
        NutritionService(StubFoodRepository(None)),  # type: ignore[arg-type]
        usda_food_reference_service=fallback,  # type: ignore[arg-type]
    )
    result = service.analyze(image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("180"))
    assert fallback.called is True
    assert result.status == "calculated"
    assert result.nutrition.calories == Decimal("180.000")


def test_calculated_analysis_exposes_v2_values_without_changing_domain_state() -> None:
    food = create_test_food()
    food.sodium_mg_per_100g = Decimal("123.456")
    food.sugars_g_per_100g = Decimal("0.000")
    food.omega_3_g_per_100g = None

    result = create_service(("Test Food",), food).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("150")
    )

    assert result.status == "calculated"
    assert result.nutrition.sodium_mg == Decimal("185.184")
    assert result.nutrition.sugars_g == Decimal("0.000")
    assert result.nutrition.omega_3_g is None


def test_no_recognized_food_returns_domain_outcome() -> None:
    result = create_service((), calculator=FailingCalculator()).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("180")
    )

    assert result.status == "food_not_recognized"
    assert result.recognized_foods == []


def test_multiple_recognized_foods_require_selection_without_calculation() -> None:
    result = create_service(
        ("Test Food", "Other Food"), calculator=FailingCalculator()
    ).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("420")
    )

    assert result.status == "requires_food_selection"
    assert [food.name for food in result.recognized_foods] == ["Test Food", "Other Food"]


def test_missing_nutrition_reference_returns_domain_outcome() -> None:
    result = create_service(("Unknown Food",), calculator=FailingCalculator()).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("180")
    )

    assert result.status == "nutrition_reference_not_found"
    assert result.recognized_foods[0].name == "Unknown Food"


@pytest.mark.parametrize("weight_grams", [Decimal("0"), Decimal("5000")])
def test_calculation_accepts_boundary_weights(weight_grams: Decimal) -> None:
    result = create_service(("Test Food",), create_test_food()).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=weight_grams
    )

    assert result.status == "calculated"
    if weight_grams == 0:
        assert result.nutrition.calories == Decimal("0.000")
    else:
        assert result.nutrition.calories == Decimal("5000.000")


def image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def post_with_service(
    service: MealAnalysisService, *, image: bytes | None = None, mime_type: str = "image/png", weight: str = "180"
):
    app.dependency_overrides[get_meal_analysis_service] = lambda: service
    try:
        return TestClient(app).post(
            "/api/meals/analyze",
            data={"weight_grams": weight},
            files={"file": ("meal.png", image if image is not None else image_bytes(), mime_type)},
        )
    finally:
        app.dependency_overrides.clear()


def test_meal_analysis_endpoint_returns_typed_calculated_response() -> None:
    response = post_with_service(create_service(("Test Food",), create_test_food()))

    assert response.status_code == 200
    assert response.json()["status"] == "calculated"
    assert response.json()["nutrition"]["calories"] == "180.000"


def test_meal_analysis_endpoint_rejects_invalid_image() -> None:
    response = post_with_service(
        create_service(("Test Food",), create_test_food()), image=b"not-an-image"
    )

    assert response.status_code == 422


def test_meal_analysis_endpoint_rejects_unsupported_mime_type() -> None:
    response = post_with_service(
        create_service(("Test Food",), create_test_food()), mime_type="image/gif"
    )

    assert response.status_code == 415


@pytest.mark.parametrize("weight", ["-0.1", "5000.1", "NaN", "Infinity", "invalid"])
def test_meal_analysis_endpoint_rejects_invalid_weight(weight: str) -> None:
    response = post_with_service(
        create_service(("Test Food",), create_test_food()), weight=weight
    )

    assert response.status_code == 422
