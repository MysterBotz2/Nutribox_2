from decimal import Decimal

from app.models.food import Food, normalize_food_name
from app.models.user import User
from app.models.user_recipe import UserRecipe, UserRecipeIngredient
from app.repositories.food_repository import FoodRepository
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.repositories.user_recipe_repository import UserRecipeRepository
from app.schemas.meal import MealAnalysisStatus
from app.schemas.meal_analysis_session import ComponentResolutionStatus
from app.services.composite_dish_estimator import CompositeDishEstimate, CompositeDishEstimator, CompositeIngredientEstimate
from app.services.food_recognition_provider import FoodRecognitionProvider, FoodRecognitionResult, RecognizedMealComponent
from app.services.meal_analysis_service import MealAnalysisService
from app.services.meal_analysis_session_service import MealAnalysisSessionService
from app.services.nutrition_service import NutritionService


class _Recognition(FoodRecognitionProvider):
    def __init__(self) -> None:
        self.calls = 0

    def recognize_food(self, *, image_bytes: bytes, content_type: str) -> FoodRecognitionResult:
        self.calls += 1
        return FoodRecognitionResult(
            source="simulated",
            components=(RecognizedMealComponent("Pork Sinigang", Decimal("1")),),
        )


class _Estimator(CompositeDishEstimator):
    def __init__(self) -> None:
        self.calls = 0

    def estimate_composition(self, *, dish_name: str, dish_weight_grams: Decimal) -> CompositeDishEstimate:
        self.calls += 1
        return CompositeDishEstimate(
            dish_name,
            (
                CompositeIngredientEstimate("Pork", Decimal("0.6")),
                CompositeIngredientEstimate("Broth", Decimal("0.4")),
            ),
        )


def _user(email: str) -> User:
    return User(email=email, password_hash="x", first_name="Recipe", last_name="User")


def _food(identifier: int, name: str, calories: str) -> Food:
    return Food(
        id=identifier, name=name, normalized_name=normalize_food_name(name),
        calories_per_100g=Decimal(calories), protein_g_per_100g=Decimal("10"),
        carbohydrates_g_per_100g=Decimal("20"), fat_g_per_100g=Decimal("3"), fiber_g_per_100g=Decimal("2"),
        source_name="Local reference", source_type="local_database", source_reference=f"food:{identifier}", is_verified=True,
    )


def _recipe(user: User, name: str = "Pork Sinigang") -> UserRecipe:
    return UserRecipe(
        user=user, name=name, normalized_name=normalize_food_name(name),
        ingredients=[
            UserRecipeIngredient(position=1, name_snapshot="Pork", normalized_name="pork", normalized_proportion=Decimal("0.600000000"), nutrition_source_type="local_database", resolved_reference="food:1", ingredient_source="user_confirmed", weight_source="user_confirmed"),
            UserRecipeIngredient(position=2, name_snapshot="Broth", normalized_name="broth", normalized_proportion=Decimal("0.400000000"), nutrition_source_type="local_database", resolved_reference="food:2", ingredient_source="user_confirmed", weight_source="ai_estimate"),
        ],
    )


def _service(database_session, recognition: _Recognition, estimator: _Estimator | None) -> MealAnalysisService:
    return MealAnalysisService(
        recognition,
        NutritionService(FoodRepository(database_session)),
        composite_dish_estimator=estimator,
        user_recipe_repository=UserRecipeRepository(database_session),
    )


def _sessions(database_session) -> MealAnalysisSessionService:
    return MealAnalysisSessionService(MealAnalysisSessionRepository(database_session))


def test_exact_personal_recipe_match_requires_explicit_choice_and_preserves_variants(database_session) -> None:
    user = _user("reuse-match@example.com")
    other = _user("reuse-other@example.com")
    database_session.add_all([user, other, _food(1, "Pork", "200"), _food(2, "Broth", "10")])
    database_session.flush()
    first = _recipe(user, "Pork Sinigang")
    second = _recipe(user, " pork   sinigang ")
    foreign = _recipe(other, "Pork Sinigang")
    database_session.add_all([first, second, foreign]); database_session.flush()
    recognition, estimator = _Recognition(), _Estimator()
    service = _service(database_session, recognition, estimator)

    result = service.analyze_composed(user_id=user.id, image_bytes=b"image", content_type="image/jpeg", measured_weight_grams=Decimal("275.000"), session_service=_sessions(database_session))

    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_RECIPE_CONFIRMATION
    component = result.state.components[0]
    assert component.resolution_status == ComponentResolutionStatus.REQUIRES_RECIPE_CONFIRMATION
    assert [match.recipe_id for match in component.recipe_matches] == [second.id, first.id]
    assert all(match.recipe_id != foreign.id for match in component.recipe_matches)
    assert component.nutrition is None
    assert estimator.calls == 0 and recognition.calls == 1


def test_use_recipe_scales_exact_references_without_estimator_or_recognition(database_session) -> None:
    user = _user("reuse-use@example.com")
    database_session.add_all([user, _food(1, "Pork", "200"), _food(2, "Broth", "10")])
    database_session.flush()
    recipe = _recipe(user); database_session.add(recipe); database_session.flush()
    recognition, estimator = _Recognition(), _Estimator()
    service = _service(database_session, recognition, estimator)
    initial = service.analyze_composed(user_id=user.id, image_bytes=b"image", content_type="image/jpeg", measured_weight_grams=Decimal("275.000"), session_service=_sessions(database_session))
    assert initial is not None
    component_id = str(initial.state.components[0].component_id)

    result = service.use_personal_recipe(user_id=user.id, session_id=initial.session_id, component_id=component_id, recipe_id=recipe.id, session_service=_sessions(database_session))

    component = result.state.components[0]
    provenance = component.composite_provenance_snapshot
    assert result.status == MealAnalysisStatus.CALCULATED
    assert estimator.calls == 0 and recognition.calls == 1
    assert provenance is not None and provenance.composition_source == "personal_recipe"
    assert provenance.recipe_id == recipe.id and provenance.recipe_name_snapshot == recipe.name
    assert [ingredient.source_reference_id for ingredient in provenance.ingredients] == ["food:1", "food:2"]
    assert [ingredient.estimated_weight_grams for ingredient in provenance.ingredients] == [Decimal("165.000"), Decimal("110.000")]
    assert sum((ingredient.estimated_weight_grams for ingredient in provenance.ingredients), Decimal("0")) == Decimal("275.000")
    assert component.nutrition is not None and component.nutrition["calories"] == "341.000"
    assert [ingredient.normalized_proportion for ingredient in recipe.ingredients] == [Decimal("0.600000000"), Decimal("0.400000000")]


def test_review_recipe_uses_existing_verification_state_and_analyze_as_new_bypasses_match(database_session) -> None:
    user = _user("reuse-review@example.com")
    database_session.add_all([user, _food(1, "Pork", "200"), _food(2, "Broth", "10")]); database_session.flush()
    recipe = _recipe(user); database_session.add(recipe); database_session.flush()
    recognition, estimator = _Recognition(), _Estimator()
    service = _service(database_session, recognition, estimator)
    reviewed = service.analyze_composed(user_id=user.id, image_bytes=b"image", content_type="image/jpeg", measured_weight_grams=Decimal("200.000"), session_service=_sessions(database_session))
    assert reviewed is not None
    reviewed_result = service.review_personal_recipe(user_id=user.id, session_id=reviewed.session_id, component_id=str(reviewed.state.components[0].component_id), recipe_id=recipe.id, session_service=_sessions(database_session))
    reviewed_component = reviewed_result.state.components[0]
    assert reviewed_result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert reviewed_component.resolution_status == ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert all(item.recipe_derived for item in reviewed_component.suggested_ingredients)
    assert estimator.calls == 0

    fresh = service.analyze_composed(user_id=user.id, image_bytes=b"image", content_type="image/jpeg", measured_weight_grams=Decimal("200.000"), session_service=_sessions(database_session))
    assert fresh is not None
    new_result = service.analyze_component_as_new(user_id=user.id, session_id=fresh.session_id, component_id=str(fresh.state.components[0].component_id), session_service=_sessions(database_session))
    assert new_result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert estimator.calls == 1 and recognition.calls == 2
    assert new_result.state.components[0].recipe_matches == []


def test_no_match_falls_through_to_estimator(database_session) -> None:
    user = _user("reuse-no-match@example.com"); database_session.add(user); database_session.flush()
    recognition, estimator = _Recognition(), _Estimator()
    service = _service(database_session, recognition, estimator)
    result = service.analyze_composed(user_id=user.id, image_bytes=b"image", content_type="image/jpeg", measured_weight_grams=Decimal("200.000"), session_service=_sessions(database_session))
    assert result is not None and result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
    assert estimator.calls == 1
