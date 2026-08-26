from dataclasses import dataclass
from decimal import Decimal
import logging

import httpx
import pytest
from google.genai import errors

from app.models.food import Food, normalize_food_name
from app.models.user import User
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.repositories.meal_repository import MealRepository
from app.schemas.meal import MealAnalysisStatus
from app.schemas.meal import IngredientVerificationItemRequest
from app.schemas.meal_analysis_session import ComponentResolutionStatus, IngredientResolutionStatus
from app.services.composite_dish_estimator import (
    CompositeDishEstimate,
    CompositeDishEstimator,
    CompositeDishEstimatorError,
    CompositeIngredientEstimate,
)
from app.services.food_recognition_provider import FoodRecognitionProvider, FoodRecognitionResult, RecognizedMealComponent
from app.services.gemini_composite_dish_estimator import GeminiCompositeDishEstimator
from app.services.meal_analysis_service import MealAnalysisService
from app.services.meal_analysis_session_service import MealAnalysisSessionService
from app.services.meal_service import MealService
from app.services.nutrition_service import NutritionService
from app.services.usda_food_reference_service import UsdaResolution
from app.services.usda_food_data_client import UsdaSearchFood


def _food(name: str, *, identifier: int, calories: str = "100") -> Food:
    return Food(
        id=identifier, name=name, normalized_name=normalize_food_name(name), category="test",
        calories_per_100g=Decimal(calories), protein_g_per_100g=Decimal("10"),
        carbohydrates_g_per_100g=Decimal("20"), fat_g_per_100g=Decimal("3"), fiber_g_per_100g=Decimal("2"),
        source_name="Test reference", source_type="local_database", source_reference=f"food:{identifier}", is_verified=False,
    )


class _Foods:
    def __init__(self, foods: list[Food]) -> None:
        self._foods = {food.normalized_name: food for food in foods}
        self._by_id = {food.id: food for food in foods}

    def get_by_normalized_name(self, name: str) -> Food | None:
        return self._foods.get(name)

    def get_by_id(self, identifier: int) -> Food | None:
        return self._by_id.get(identifier)


class _Recognition(FoodRecognitionProvider):
    def __init__(self, components: tuple[RecognizedMealComponent, ...]) -> None:
        self.components = components
        self.calls = 0

    def recognize_food(self, *, image_bytes: bytes, content_type: str) -> FoodRecognitionResult:
        self.calls += 1
        return FoodRecognitionResult(source="simulated", components=self.components)


class _Estimator(CompositeDishEstimator):
    def __init__(self, estimate: CompositeDishEstimate) -> None:
        self.estimate = estimate
        self.calls: list[str] = []

    def estimate_composition(self, *, dish_name: str, dish_weight_grams: Decimal) -> CompositeDishEstimate:
        self.calls.append(dish_name)
        return self.estimate


class _FailingEstimator(CompositeDishEstimator):
    def estimate_composition(self, *, dish_name: str, dish_weight_grams: Decimal) -> CompositeDishEstimate:
        raise CompositeDishEstimatorError("Composite dish estimation provider timed out.", 504)


class _NoDirectUsda:
    def __init__(self, *, ambiguous_internal: bool = False) -> None:
        self.ambiguous_internal = ambiguous_internal
        self.calls: list[str] = []

    def resolve(self, name: str) -> UsdaResolution:
        self.calls.append(name)
        if self.ambiguous_internal and name == "broth":
            return UsdaResolution(candidate_names=("Broth one", "Broth two"))
        return UsdaResolution()


def _estimate() -> CompositeDishEstimate:
    return CompositeDishEstimate(
        "pork sinigang",
        (
            CompositeIngredientEstimate("cooked pork", Decimal("0.35")),
            CompositeIngredientEstimate("broth", Decimal("0.40")),
            CompositeIngredientEstimate("mixed vegetables", Decimal("0.25")),
        ),
    )


@pytest.mark.parametrize("ingredients", [(), (CompositeIngredientEstimate("", Decimal("1")),), (CompositeIngredientEstimate("pork", Decimal("-1")),), (CompositeIngredientEstimate("pork", Decimal("0")),)])
def test_composite_estimate_rejects_empty_invalid_and_zero_compositions(ingredients) -> None:
    with pytest.raises(ValueError):
        CompositeDishEstimate("dish", ingredients)


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_composite_estimate_rejects_non_finite_proportions(value: Decimal) -> None:
    with pytest.raises(ValueError):
        CompositeDishEstimate("dish", (CompositeIngredientEstimate("ingredient", value),))


def test_composite_estimate_preserves_decimal_proportions() -> None:
    estimate = _estimate()
    assert estimate.ingredients[0].estimated_proportion == Decimal("0.35")


def test_composite_fallback_resolves_pork_sinigang_without_changing_top_level_weights(database_session) -> None:
    user = User(email="sinigang@example.com", password_hash="x", first_name="Sinigang", last_name="Test")
    database_session.add(user)
    database_session.flush()
    recognition = _Recognition((
        RecognizedMealComponent("pork sinigang", Decimal("0.55")),
        RecognizedMealComponent("steamed white rice", Decimal("0.40")),
        RecognizedMealComponent("chili fish sauce", Decimal("0.05")),
    ))
    estimator = _Estimator(_estimate())
    usda = _NoDirectUsda()
    foods = [
        _food("steamed white rice", identifier=1, calories="130"),
        _food("chili fish sauce", identifier=2, calories="50"),
        _food("cooked pork", identifier=3, calories="200"),
        _food("broth", identifier=4, calories="10"),
        _food("mixed vegetables", identifier=5, calories="30"),
    ]
    database_session.add_all(foods)
    database_session.flush()
    repository = _Foods(foods)
    service = MealAnalysisService(
        recognition,
        NutritionService(repository),  # type: ignore[arg-type]
        usda_food_reference_service=usda,  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    )
    result = service.analyze_composed(
        user_id=user.id, image_bytes=b"image", content_type="image/jpeg", measured_weight_grams=Decimal("500.000"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert recognition.calls == 1
    assert estimator.calls == ["pork sinigang"]
    sinigang, rice, fish_sauce = result.state.components
    assert sinigang.resolution_status == ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert sinigang.composite_provenance_snapshot is None
    assert sinigang.nutrition is None
    assert len(sinigang.suggested_ingredients) == 3
    verified = service.verify_ingredients(
        user_id=user.id,
        session_id=result.session_id,
        component_id=str(sinigang.component_id),
        ingredients=[IngredientVerificationItemRequest(ingredient_id=item.ingredient_id, name=item.name, included=True) for item in sinigang.suggested_ingredients],
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )
    assert verified.status == MealAnalysisStatus.CALCULATED
    sinigang = verified.state.components[0]
    assert [item.estimated_weight_grams for item in result.state.components] == [Decimal("275.000"), Decimal("200.000"), Decimal("25.000")]
    assert rice.nutrition_source == "local_database" and fish_sauce.nutrition_source == "local_database"
    assert sinigang.nutrition_source == "ai_recipe_estimate"
    assert sinigang.composite_provenance_snapshot is not None
    assert sinigang.composite_provenance_snapshot.composition_source == "user_confirmed"
    assert sum((item.estimated_weight_grams for item in sinigang.composite_provenance_snapshot.ingredients), Decimal("0")) == Decimal("275.000")
    assert [item.source_reference_id for item in sinigang.composite_provenance_snapshot.ingredients] == ["food:3", "food:4", "food:5"]
    assert verified.nutrition is not None and verified.nutrition.calories == Decimal("496.625")
    meal = MealService(
        NutritionService(repository), MealRepository(database_session)  # type: ignore[arg-type]
    ).create_meal_from_analysis_session(verified.session_id, user.id)
    assert len(meal.items) == 3
    composite_item = next(item for item in meal.items if item.food_id is None)
    assert composite_item.food_name_snapshot == "pork sinigang"
    assert composite_item.nutrition_source_type == "ai_recipe_estimate"
    assert composite_item.composite_provenance_snapshot is not None


def test_composite_estimator_is_not_called_when_direct_reference_exists(database_session) -> None:
    user = User(email="direct-composite@example.com", password_hash="x", first_name="Direct", last_name="Test")
    database_session.add(user); database_session.flush()
    estimator = _Estimator(_estimate())
    service = MealAnalysisService(
        _Recognition((RecognizedMealComponent("beef stew", Decimal("1")),)),
        NutritionService(_Foods([_food("beef stew", identifier=1)])),  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    )
    result = service.analyze_composed(user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("100.000"), session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)))
    assert result is not None and result.status == MealAnalysisStatus.CALCULATED
    assert estimator.calls == []


def test_live_like_sinigang_rice_and_chili_fixture_only_needs_sauce_selection(database_session) -> None:
    user = User(email="sinigang-sauce@example.com", password_hash="x", first_name="Sinigang", last_name="Sauce")
    database_session.add(user); database_session.flush()

    class StrictTopReferences:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def resolve(self, name: str) -> UsdaResolution:
            self.calls.append(name)
            if name == "steamed rice":
                rice = _food("Rice, white, steamed, Chinese restaurant", identifier=40, calories="130")
                rice.source_type = "USDA"; rice.source_reference = "fdcId:40"
                return UsdaResolution(food=rice)
            if name == "chili dipping sauce":
                return UsdaResolution(candidates=(
                    UsdaSearchFood(51, "Tomato chili sauce", "Survey (FNDDS)"),
                    UsdaSearchFood(52, "Sauce, tomato chili sauce, bottled, with salt", "Survey (FNDDS)"),
                ))
            return UsdaResolution()

    estimator = _Estimator(_estimate())
    references = StrictTopReferences()
    recognition = _Recognition((
        RecognizedMealComponent("pork sinigang", Decimal("0.55")),
        RecognizedMealComponent("steamed rice", Decimal("0.40")),
        RecognizedMealComponent("chili dipping sauce", Decimal("0.05")),
    ))
    result = MealAnalysisService(
        recognition,
        NutritionService(_Foods([
            _food("cooked pork", identifier=1), _food("broth", identifier=2), _food("mixed vegetables", identifier=3),
        ])),  # type: ignore[arg-type]
        usda_food_reference_service=references,  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    ).analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("500.000"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_FOOD_SELECTION
    sinigang, rice, sauce = result.state.components
    assert [item.estimated_weight_grams for item in result.state.components] == [Decimal("275.000"), Decimal("200.000"), Decimal("25.000")]
    assert sinigang.resolution_status == ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert sinigang.nutrition_source is None
    assert sinigang.composite_provenance_snapshot is None
    assert len(sinigang.suggested_ingredients) == 3
    assert rice.nutrition_source == "USDA"
    assert sauce.resolution_status == ComponentResolutionStatus.REQUIRES_FOOD_SELECTION
    assert [candidate["name"] for candidate in sauce.candidates] == ["Tomato chili sauce", "Sauce, tomato chili sauce, bottled, with salt"]
    assert estimator.calls == ["pork sinigang"]
    assert recognition.calls == 1


def test_ambiguous_or_missing_internal_ingredient_fails_without_nested_selection(database_session) -> None:
    user = User(email="ambiguous-internal@example.com", password_hash="x", first_name="Internal", last_name="Test")
    database_session.add(user); database_session.flush()
    estimator = _Estimator(_estimate())
    usda = _NoDirectUsda(ambiguous_internal=True)
    result = MealAnalysisService(
        _Recognition((RecognizedMealComponent("pork sinigang", Decimal("1")),)),
        NutritionService(_Foods([_food("cooked pork", identifier=1), _food("mixed vegetables", identifier=2)])),  # type: ignore[arg-type]
        usda_food_reference_service=usda,  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    ).analyze_composed(user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("275.000"), session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)))
    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert result.state.components[0].resolution_status == ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert result.state.components[0].nutrition is None
    assert len(result.state.components[0].suggested_ingredients) == 3
    assert estimator.calls == ["pork sinigang"]
    assert usda.calls == ["pork sinigang"]


def test_composite_fallback_ineligible_component_does_not_call_estimator(database_session, caplog) -> None:
    caplog.set_level(logging.INFO)
    user = User(email="ineligible-composite@example.com", password_hash="x", first_name="Test", last_name="User")
    database_session.add(user); database_session.flush()
    estimator = _Estimator(_estimate())
    result = MealAnalysisService(
        _Recognition((RecognizedMealComponent("unknown side", Decimal("1")),)),
        NutritionService(_Foods([])),  # type: ignore[arg-type]
        usda_food_reference_service=_NoDirectUsda(),  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    ).analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("100"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND
    assert estimator.calls == []
    assert "eligibility=False estimator_called=false" in caplog.text


def test_composite_fallback_logs_not_found_internal_reason(database_session, caplog) -> None:
    caplog.set_level(logging.INFO)
    user = User(email="not-found-composite@example.com", password_hash="x", first_name="Test", last_name="User")
    database_session.add(user); database_session.flush()
    estimator = _Estimator(_estimate())
    result = MealAnalysisService(
        _Recognition((RecognizedMealComponent("pork sinigang", Decimal("1")),)),
        NutritionService(_Foods([_food("cooked pork", identifier=1), _food("mixed vegetables", identifier=2)])),  # type: ignore[arg-type]
        usda_food_reference_service=_NoDirectUsda(),  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    ).analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("275"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert result.state.components[0].nutrition is None
    assert len(result.state.components[0].suggested_ingredients) == 3
    assert "estimator_outcome=success ingredient_count=3" in caplog.text


def test_composite_fallback_logs_ambiguous_internal_reason(database_session, caplog) -> None:
    caplog.set_level(logging.INFO)
    user = User(email="ambiguous-composite@example.com", password_hash="x", first_name="Test", last_name="User")
    database_session.add(user); database_session.flush()
    estimator = _Estimator(_estimate())
    result = MealAnalysisService(
        _Recognition((RecognizedMealComponent("pork sinigang", Decimal("1")),)),
        NutritionService(_Foods([_food("cooked pork", identifier=1), _food("mixed vegetables", identifier=2)])),  # type: ignore[arg-type]
        usda_food_reference_service=_NoDirectUsda(ambiguous_internal=True),  # type: ignore[arg-type]
        composite_dish_estimator=estimator,
    ).analyze_composed(
        user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("275"),
        session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )

    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert result.state.components[0].nutrition is None
    assert len(result.state.components[0].suggested_ingredients) == 3


def test_composite_fallback_preserves_estimator_errors(database_session, caplog) -> None:
    caplog.set_level(logging.INFO)
    user = User(email="provider-error-composite@example.com", password_hash="x", first_name="Test", last_name="User")
    database_session.add(user); database_session.flush()
    service = MealAnalysisService(
        _Recognition((RecognizedMealComponent("pork sinigang", Decimal("1")),)),
        NutritionService(_Foods([])),  # type: ignore[arg-type]
        usda_food_reference_service=_NoDirectUsda(),  # type: ignore[arg-type]
        composite_dish_estimator=_FailingEstimator(),
    )

    with pytest.raises(CompositeDishEstimatorError) as raised:
        service.analyze_composed(
            user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("275"),
            session_service=MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
        )

    assert raised.value.status_code == 504
    assert "estimator_outcome=provider_error" in caplog.text


def test_ingredient_candidate_id_selects_exact_duplicate_name_reference_and_reevaluates(database_session) -> None:
    user = User(email="candidate-id@example.com", password_hash="x", first_name="Candidate", last_name="Test")
    database_session.add(user); database_session.flush()
    selected = _food("Pork, cooked", identifier=222, calories="300")
    repository = _Foods([selected, _food("broth", identifier=2), _food("mixed vegetables", identifier=3)])
    repository._foods.pop(normalize_food_name("Pork, cooked"))

    class DuplicateNameReferences:
        def __init__(self) -> None: self.loaded: list[int] = []
        def resolve(self, name: str) -> UsdaResolution:
            if name == "pork sinigang": return UsdaResolution()
            if name == "cooked pork": return UsdaResolution(candidates=(UsdaSearchFood(111, "Pork, cooked", "USDA"), UsdaSearchFood(222, "Pork, cooked", "USDA")))
            return UsdaResolution()
        def load_by_fdc_id(self, fdc_id: int):
            self.loaded.append(fdc_id)
            return selected if fdc_id == 222 else None

    recognition = _Recognition((RecognizedMealComponent("pork sinigang", Decimal("1")),))
    estimator = _Estimator(_estimate())
    references = DuplicateNameReferences()
    service = MealAnalysisService(recognition, NutritionService(repository), usda_food_reference_service=references, composite_dish_estimator=estimator)  # type: ignore[arg-type]
    sessions = MealAnalysisSessionService(MealAnalysisSessionRepository(database_session))
    analysis = service.analyze_composed(user_id=user.id, image_bytes=b"x", content_type="image/jpeg", measured_weight_grams=Decimal("275.000"), session_service=sessions)
    assert analysis is not None and analysis.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    component = analysis.state.components[0]
    verified = service.verify_ingredients(user_id=user.id, session_id=analysis.session_id, component_id=str(component.component_id), ingredients=[IngredientVerificationItemRequest(ingredient_id=item.ingredient_id, name=item.name, included=True) for item in component.suggested_ingredients], session_service=sessions)
    component = verified.state.components[0]
    pork = next(item for item in component.suggested_ingredients if item.name == "cooked pork")
    assert pork.resolution_status == IngredientResolutionStatus.REQUIRES_FOOD_SELECTION
    assert [item["source_reference_id"] for item in pork.candidates] == ["111", "222"]
    selected_candidate = pork.candidates[1]["candidate_id"]
    with pytest.raises(ValueError):
        service.apply_ingredient_selection(user_id=user.id, session_id=analysis.session_id, component_id=str(component.component_id), ingredient_id=str(component.suggested_ingredients[1].ingredient_id), candidate_id=selected_candidate, session_service=sessions)
    final = service.apply_ingredient_selection(user_id=user.id, session_id=analysis.session_id, component_id=str(component.component_id), ingredient_id=str(pork.ingredient_id), candidate_id=selected_candidate, session_service=sessions)
    composite = final.state.components[0]
    assert references.loaded == [222]
    assert final.status == MealAnalysisStatus.CALCULATED
    assert composite.resolution_status == ComponentResolutionStatus.RESOLVED
    assert composite.composite_provenance_snapshot is not None
    assert composite.composite_provenance_snapshot.composition_source == "user_confirmed"
    assert composite.composite_provenance_snapshot.ingredients[0].source_reference_id == "food:222"
    assert sum(item.estimated_weight_grams for item in composite.composite_provenance_snapshot.ingredients) == Decimal("275.000")
    assert recognition.calls == 1 and estimator.calls == ["pork sinigang"]


@dataclass
class _Response:
    parsed: object


class _Models:
    def __init__(self, response: object | Exception) -> None:
        self.response = response
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class _Client:
    def __init__(self, response: object | Exception) -> None:
        self.models = _Models(response)


def test_gemini_estimator_rejects_nutrients_and_maps_safe_provider_errors() -> None:
    provider = GeminiCompositeDishEstimator(api_key="test", model="test", timeout_seconds=1, client=_Client(_Response({"ingredients": [{"name": "pork", "estimated_proportion": "1", "calories": "100"}]})))
    with pytest.raises(CompositeDishEstimatorError, match="invalid response"):
        provider.estimate_composition(dish_name="pork sinigang", dish_weight_grams=Decimal("275"))

    provider = GeminiCompositeDishEstimator(api_key="test", model="test", timeout_seconds=1, client=_Client(httpx.TimeoutException("timeout")))
    with pytest.raises(CompositeDishEstimatorError) as raised:
        provider.estimate_composition(dish_name="pork sinigang", dish_weight_grams=Decimal("275"))
    assert raised.value.status_code == 504


def test_gemini_estimator_returns_proportions_only_with_a_separate_prompt() -> None:
    client = _Client(_Response({"ingredients": [{"name": "cooked pork", "estimated_proportion": "0.4"}, {"name": "broth", "estimated_proportion": "0.6"}]}))
    provider = GeminiCompositeDishEstimator(api_key="test", model="test", timeout_seconds=1, client=client)
    estimate = provider.estimate_composition(dish_name="pork sinigang", dish_weight_grams=Decimal("275"))
    assert [item.name for item in estimate.ingredients] == ["cooked pork", "broth"]
    assert [item.estimated_proportion for item in estimate.ingredients] == [Decimal("0.4"), Decimal("0.6")]
    prompt = client.models.calls[0]["contents"][0].casefold()
    assert "do not provide calories" in prompt
    assert "top-level" not in prompt


@pytest.mark.parametrize(
    "payload",
    [
        {"ingredients": []},
        {},
        {"ingredients": [{"name": "   ", "estimated_proportion": 1}]},
        {"ingredients": [{"name": "pork", "estimated_proportion": -1}]},
        {"ingredients": [{"name": "pork", "estimated_proportion": 0}]},
        {"ingredients": [{"name": "pork", "estimated_proportion": "NaN"}]},
        {"ingredients": [{"name": "pork", "estimated_proportion": "Infinity"}]},
        {"ingredients": [{"name": "pork", "estimated_proportion": 1, "calories": 100}]},
        {"components": []},
        "```json\n{\"ingredients\": []}\n```",
    ],
)
def test_gemini_estimator_rejects_invalid_structured_output(payload: object) -> None:
    provider = GeminiCompositeDishEstimator(
        api_key="test", model="test", timeout_seconds=1, client=_Client(_Response(payload))
    )

    with pytest.raises(CompositeDishEstimatorError, match="invalid response") as raised:
        provider.estimate_composition(dish_name="pork sinigang", dish_weight_grams=Decimal("275"))

    assert raised.value.status_code == 502


def test_gemini_estimator_uses_native_sdk_schema_and_logs_success(caplog) -> None:
    caplog.set_level(logging.INFO)
    client = _Client(
        _Response({"ingredients": [{"name": "cooked pork", "estimated_proportion": 1}]})
    )
    provider = GeminiCompositeDishEstimator(api_key="test", model="test-model", timeout_seconds=1, client=client)

    provider.estimate_composition(dish_name="pork sinigang", dish_weight_grams=Decimal("275"))

    config = client.models.calls[0]["config"]
    assert config.response_schema.type.value == "OBJECT"
    assert "outcome=success" in caplog.text
    assert "ingredient_count=1" in caplog.text


def test_gemini_estimator_distinguishes_provider_400_from_invalid_output(caplog) -> None:
    provider = GeminiCompositeDishEstimator(
        api_key="test",
        model="test-model",
        timeout_seconds=1,
        client=_Client(errors.ClientError(400, {"error": {"status": "INVALID_ARGUMENT"}})),
    )

    with pytest.raises(CompositeDishEstimatorError, match="request failed") as raised:
        provider.estimate_composition(dish_name="pork sinigang", dish_weight_grams=Decimal("275"))

    assert raised.value.status_code == 502
    assert "outcome=provider_request_failure" in caplog.text
    assert "provider_status_code=400" in caplog.text
