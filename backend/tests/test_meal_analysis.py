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
    FoodRecognitionProviderError,
    FoodRecognitionResult,
    RecognizedMealComponent,
)
from app.models.user import User
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.services.meal_analysis_session_service import MealAnalysisSessionService
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


class ComponentFoodRecognitionProvider(FoodRecognitionProvider):
    def __init__(self, components: tuple[RecognizedMealComponent, ...]) -> None:
        self._components = components

    def recognize_food(self, *, image_bytes: bytes, content_type: str) -> FoodRecognitionResult:
        return FoodRecognitionResult(source="simulated", components=self._components)


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


def test_usda_ranked_candidates_preserve_existing_selection_outcome() -> None:
    class AmbiguousUsdaFallback:
        def resolve(self, _: str) -> UsdaResolution:
            return UsdaResolution(candidate_names=("Chicken wing, fried", "Chicken thigh, fried"))

    result = MealAnalysisService(
        StubFoodRecognitionProvider(("fried chicken",)),
        NutritionService(StubFoodRepository(None)),  # type: ignore[arg-type]
        usda_food_reference_service=AmbiguousUsdaFallback(),  # type: ignore[arg-type]
    ).analyze(image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("180"))

    assert result.status == "requires_food_selection"
    assert [food.name for food in result.recognized_foods] == ["Chicken wing, fried", "Chicken thigh, fried"]


def test_usda_no_relevant_candidates_preserves_not_found_outcome() -> None:
    class EmptyUsdaFallback:
        def resolve(self, _: str) -> UsdaResolution:
            return UsdaResolution()

    result = MealAnalysisService(
        StubFoodRecognitionProvider(("fried chicken",)),
        NutritionService(StubFoodRepository(None)),  # type: ignore[arg-type]
        usda_food_reference_service=EmptyUsdaFallback(),  # type: ignore[arg-type]
    ).analyze(image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("180"))

    assert result.status == "nutrition_reference_not_found"


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


@pytest.mark.parametrize(
    ("provider_status", "provider_detail", "expected_status", "expected_detail"),
    [
        (
            429,
            "Food recognition provider rate limit was reached: quota-identifier.",
            503,
            "Food recognition service is temporarily unavailable. Please try again later.",
        ),
        (504, "Food recognition provider timed out.", 504, "Food recognition provider timed out."),
        (503, "Food recognition provider is unavailable.", 503, "Food recognition provider is unavailable."),
    ],
)
def test_meal_analysis_endpoint_normalizes_provider_failures(
    provider_status: int,
    provider_detail: str,
    expected_status: int,
    expected_detail: str,
) -> None:
    class FailingProvider(FoodRecognitionProvider):
        def recognize_food(self, *, image_bytes: bytes, content_type: str) -> FoodRecognitionResult:
            raise FoodRecognitionProviderError(provider_detail, provider_status)

    service = MealAnalysisService(
        FailingProvider(),
        NutritionService(StubFoodRepository(None)),  # type: ignore[arg-type]
    )

    response = post_with_service(service)

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    if provider_status == 429:
        assert "quota-identifier" not in response.text


@pytest.mark.parametrize(
    ("recognized_names", "expected_analysis_status"),
    [
        (("Unknown Food",), "nutrition_reference_not_found"),
        (("Food One", "Food Two"), "requires_food_selection"),
    ],
)
def test_meal_analysis_endpoint_keeps_normal_analysis_states_as_successes(
    recognized_names: tuple[str, ...], expected_analysis_status: str
) -> None:
    response = post_with_service(create_service(recognized_names))

    assert response.status_code == 200
    assert response.json()["status"] == expected_analysis_status


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


def test_composed_analysis_allocates_resolves_aggregates_and_creates_session(database_session) -> None:
    class Foods:
        def __init__(self):
            self.foods = {
                "rice": create_test_food(),
                "fried chicken": create_test_food(),
                "mixed vegetables": create_test_food(),
            }
            for name, food in self.foods.items():
                food.id = len(name)
                food.name = name.title()
                food.normalized_name = name
                food.source_reference = f"local:{name}"

        def get_by_normalized_name(self, name): return self.foods.get(name)

    user = User(email="composed@example.com", password_hash="x", first_name="Composed", last_name="User")
    database_session.add(user); database_session.flush()
    service = MealAnalysisService(
        ComponentFoodRecognitionProvider((
            RecognizedMealComponent("rice", Decimal("0.50")),
            RecognizedMealComponent("fried chicken", Decimal("0.30")),
            RecognizedMealComponent("mixed vegetables", Decimal("0.20")),
        )),
        NutritionService(Foods()),  # type: ignore[arg-type]
    )
    result = service.analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("500.000"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == "calculated"
    assert [component.estimated_weight_grams for component in result.state.components] == [Decimal("250.000"), Decimal("150.000"), Decimal("100.000")]
    assert sum((component.estimated_weight_grams for component in result.state.components), Decimal()) == Decimal("500.000")
    assert len({component.component_id for component in result.state.components}) == 3
    assert all(component.weight_source == "ai_estimate" for component in result.state.components)
    assert all(component.nutrition is not None for component in result.state.components)
    persisted = MealAnalysisSessionRepository(database_session).get_for_user(result.session_id, user.id)
    assert persisted is not None and persisted.status == "calculated"


def test_composed_analysis_preserves_resolved_components_when_one_is_ambiguous(database_session) -> None:
    class Foods(StubFoodRepository):
        def get_by_normalized_name(self, name):
            return create_test_food() if name == "rice" else None

    class Usda:
        def resolve(self, name):
            return UsdaResolution(candidate_names=("Chicken wing, fried", "Chicken thigh, fried")) if name == "fried chicken" else UsdaResolution()

    user = User(email="composed-ambiguous@example.com", password_hash="x", first_name="Composed", last_name="User")
    database_session.add(user); database_session.flush()
    result = MealAnalysisService(
        ComponentFoodRecognitionProvider((RecognizedMealComponent("rice", Decimal("1")), RecognizedMealComponent("fried chicken", Decimal("1")))),
        NutritionService(Foods(None)),  # type: ignore[arg-type]
        usda_food_reference_service=Usda(),  # type: ignore[arg-type]
    ).analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("200.000"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == "requires_food_selection" and result.nutrition is None
    resolved, ambiguous = result.state.components
    assert resolved.nutrition is not None and resolved.resolved_reference is not None
    assert ambiguous.nutrition is None and ambiguous.candidates == [{"name": "Chicken wing, fried"}, {"name": "Chicken thigh, fried"}]


def test_composed_analysis_no_reference_does_not_fabricate_nutrition(database_session) -> None:
    user = User(email="composed-missing@example.com", password_hash="x", first_name="Composed", last_name="User")
    database_session.add(user); database_session.flush()
    result = MealAnalysisService(
        ComponentFoodRecognitionProvider((RecognizedMealComponent("unknown", Decimal("1")),)),
        NutritionService(StubFoodRepository(None)),  # type: ignore[arg-type]
    ).analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("200.000"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )
    assert result is not None and result.status == "nutrition_reference_not_found"
    assert result.state.components[0].nutrition is None


def test_authenticated_analyze_exposes_composed_session_contract(client, auth_headers, database_session) -> None:
    class Foods:
        def get_by_normalized_name(self, name):
            food = create_test_food(); food.id = 10; food.name = name.title(); food.normalized_name = name; food.source_reference = f"local:{name}"
            return food
    service = MealAnalysisService(
        ComponentFoodRecognitionProvider((RecognizedMealComponent("rice", Decimal("0.5")), RecognizedMealComponent("fried chicken", Decimal("0.3")), RecognizedMealComponent("mixed vegetables", Decimal("0.2")))),
        NutritionService(Foods()),  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_meal_analysis_service] = lambda: service
    try:
        response = client.post("/api/meals/analyze", headers=auth_headers, data={"weight_grams": "500.000"}, files={"file": ("meal.png", image_bytes(), "image/png")})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "calculated"
    assert payload["analysis_session_id"] is not None
    assert payload["measured_weight_grams"] == "500.000"
    assert [component["estimated_weight_grams"] for component in payload["components"]] == ["250.000", "150.000", "100.000"]
