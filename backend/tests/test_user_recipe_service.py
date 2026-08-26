from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.user import User
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.repositories.user_recipe_repository import UserRecipeRepository
from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    CompositeIngredientSnapshot,
    CompositeProvenanceSnapshot,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
    WeightSource,
)
from app.services.meal_analysis_session_service import (
    MealAnalysisSessionConsumedError,
    MealAnalysisSessionExpiredError,
    MealAnalysisSessionNotFoundError,
    MealAnalysisSessionService,
)
from app.services.user_recipe_service import (
    UserRecipeNotFoundError,
    UserRecipeSaveEligibilityError,
    UserRecipeService,
)


def _user(email: str) -> User:
    return User(
        email=email,
        password_hash="not-a-real-password",
        first_name="Recipe",
        last_name="Owner",
    )


def _service(database_session) -> tuple[UserRecipeService, MealAnalysisSessionService]:
    sessions = MealAnalysisSessionService(MealAnalysisSessionRepository(database_session))
    return UserRecipeService(UserRecipeRepository(database_session), sessions), sessions


def _state(
    *,
    status: ComponentResolutionStatus = ComponentResolutionStatus.RESOLVED,
    composite: bool = True,
    confirmed: bool = True,
    missing_reference: bool = False,
) -> tuple[MealAnalysisSessionState, str]:
    component_id = str(uuid4())
    ingredients = [
        CompositeIngredientSnapshot(
            ingredient_name="Pork",
            raw_estimated_proportion=Decimal("0.333333333"),
            normalized_proportion=Decimal("0.333333333"),
            estimated_weight_grams=Decimal("100.000"),
            nutrition_source="USDA",
            source_reference_id="" if missing_reference else "fdcId:111",
            reference_name="Pork, cooked",
            nutrition={"calories": "100.000"},
            ingredient_source="user_confirmed",
            weight_source=WeightSource.USER_CONFIRMED,
        ),
        CompositeIngredientSnapshot(
            ingredient_name="Radish",
            raw_estimated_proportion=Decimal("0.333333333"),
            normalized_proportion=Decimal("0.333333333"),
            estimated_weight_grams=Decimal("100.000"),
            nutrition_source="local_database",
            source_reference_id="food:42",
            reference_name="Radish",
            nutrition={"calories": "20.000"},
            ingredient_source="user_confirmed",
            weight_source=WeightSource.AI_ESTIMATE,
        ),
        CompositeIngredientSnapshot(
            ingredient_name="Broth",
            raw_estimated_proportion=Decimal("0.333333334"),
            normalized_proportion=Decimal("0.333333334"),
            estimated_weight_grams=Decimal("100.000"),
            nutrition_source="USDA",
            source_reference_id="fdcId:333",
            reference_name="Broth",
            nutrition={"calories": "10.000"},
            ingredient_source="ai_estimate",
            weight_source=WeightSource.AI_ESTIMATE,
        ),
    ]
    provenance = (
        CompositeProvenanceSnapshot(
            dish_name="Pork Sinigang",
            dish_weight_grams=Decimal("300.000"),
            ingredients=ingredients,
            composition_source="user_confirmed" if confirmed else "ai_estimate",
        )
        if composite
        else None
    )
    component = MealAnalysisSessionComponent(
        component_id=component_id,
        recognized_name="Pork Sinigang",
        raw_estimated_proportion=Decimal("1"),
        normalized_proportion=Decimal("1"),
        estimated_weight_grams=Decimal("300.000"),
        resolution_status=status,
        nutrition_source="ai_recipe_estimate" if composite else "USDA",
        nutrition={"calories": "130.000"},
        composite_provenance_snapshot=provenance,
    )
    return MealAnalysisSessionState(measured_weight_grams=Decimal("300.000"), components=[component]), component_id


def _create_session(database_session, user: User, **kwargs):
    _, sessions = _service(database_session)
    database_session.add(user)
    database_session.flush()
    state, component_id = _state(**kwargs)
    item = sessions.create_session(user.id, state, "calculated")
    return item, component_id


def test_save_confirmed_composite_builds_exact_recipe_without_external_dependencies(database_session) -> None:
    service, _ = _service(database_session)
    owner = _user("recipe-service-owner@example.com")
    analysis_session, component_id = _create_session(database_session, owner)

    recipe = service.save_from_analysis_component(
        user_id=owner.id,
        analysis_session_id=analysis_session.id,
        component_id=component_id,
    )

    assert recipe.name == "Pork Sinigang"
    assert recipe.normalized_name == "pork sinigang"
    assert recipe.source_type == "user_confirmed"
    assert [ingredient.resolved_reference for ingredient in recipe.ingredients] == [
        "fdcId:111", "food:42", "fdcId:333"
    ]
    assert [ingredient.nutrition_source_type for ingredient in recipe.ingredients] == [
        "USDA", "local_database", "USDA"
    ]
    assert [ingredient.ingredient_source for ingredient in recipe.ingredients] == [
        "user_confirmed", "user_confirmed", "ai_estimate"
    ]
    assert [ingredient.weight_source for ingredient in recipe.ingredients] == [
        "user_confirmed", "ai_estimate", "ai_estimate"
    ]
    assert [ingredient.normalized_proportion for ingredient in recipe.ingredients] == [
        Decimal("0.333333333"), Decimal("0.333333333"), Decimal("0.333333334")
    ]
    assert sum((item.normalized_proportion for item in recipe.ingredients), Decimal("0")) == Decimal("1")


def test_save_allows_name_override_and_duplicate_recipe_variations(database_session) -> None:
    service, _ = _service(database_session)
    owner = _user("recipe-service-duplicates@example.com")
    first_session, first_component_id = _create_session(database_session, owner)
    second_session, second_component_id = _create_session(database_session, owner)

    first = service.save_from_analysis_component(
        user_id=owner.id,
        analysis_session_id=first_session.id,
        component_id=first_component_id,
        recipe_name_override="  Family Sinigang  ",
    )
    second = service.save_from_analysis_component(
        user_id=owner.id,
        analysis_session_id=second_session.id,
        component_id=second_component_id,
        recipe_name_override="Family Sinigang",
    )

    assert first.name == "Family Sinigang"
    assert first.normalized_name == "family sinigang"
    assert first.id != second.id
    assert len(service.list_for_user(owner.id)) == 2


@pytest.mark.parametrize(
    ("status", "composite", "confirmed"),
    [
        (ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION, True, True),
        (ComponentResolutionStatus.REQUIRES_FOOD_SELECTION, True, True),
        (ComponentResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND, True, True),
        (ComponentResolutionStatus.RESOLVED, False, True),
        (ComponentResolutionStatus.RESOLVED, True, False),
    ],
)
def test_save_rejects_untrusted_or_incomplete_component_states(
    database_session, status, composite, confirmed
) -> None:
    service, _ = _service(database_session)
    owner = _user(f"recipe-service-invalid-{status.value}-{composite}-{confirmed}@example.com")
    analysis_session, component_id = _create_session(
        database_session, owner, status=status, composite=composite, confirmed=confirmed
    )

    with pytest.raises(UserRecipeSaveEligibilityError):
        service.save_from_analysis_component(
            user_id=owner.id, analysis_session_id=analysis_session.id, component_id=component_id
        )


def test_save_rejects_foreign_expired_and_consumed_sessions(database_session) -> None:
    service, _ = _service(database_session)
    owner = _user("recipe-service-lifecycle-owner@example.com")
    other = _user("recipe-service-lifecycle-other@example.com")
    analysis_session, component_id = _create_session(database_session, owner)
    database_session.add(other)
    database_session.flush()

    with pytest.raises(MealAnalysisSessionNotFoundError):
        service.save_from_analysis_component(
            user_id=other.id, analysis_session_id=analysis_session.id, component_id=component_id
        )

    analysis_session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    database_session.flush()
    with pytest.raises(MealAnalysisSessionExpiredError):
        service.save_from_analysis_component(
            user_id=owner.id, analysis_session_id=analysis_session.id, component_id=component_id
        )

    analysis_session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    analysis_session.consumed_at = datetime.now(timezone.utc)
    database_session.flush()
    with pytest.raises(MealAnalysisSessionConsumedError):
        service.save_from_analysis_component(
            user_id=owner.id, analysis_session_id=analysis_session.id, component_id=component_id
        )


def test_save_rejects_malformed_composite_state_with_missing_reference(database_session) -> None:
    service, _ = _service(database_session)
    owner = _user("recipe-service-missing-reference@example.com")
    analysis_session, component_id = _create_session(database_session, owner)
    malformed_state = analysis_session.state.copy()
    malformed_state["components"][0]["composite_provenance_snapshot"]["ingredients"][0][
        "source_reference_id"
    ] = ""
    analysis_session.state = malformed_state
    database_session.flush()

    with pytest.raises(UserRecipeSaveEligibilityError):
        service.save_from_analysis_component(
            user_id=owner.id, analysis_session_id=analysis_session.id, component_id=component_id
        )


def test_save_rejects_session_not_in_calculated_lifecycle_state(database_session) -> None:
    service, _ = _service(database_session)
    owner = _user("recipe-service-not-calculated@example.com")
    analysis_session, component_id = _create_session(database_session, owner)
    analysis_session.status = "requires_ingredient_verification"
    database_session.flush()

    with pytest.raises(UserRecipeSaveEligibilityError):
        service.save_from_analysis_component(
            user_id=owner.id, analysis_session_id=analysis_session.id, component_id=component_id
        )


def test_service_owner_scoped_get_list_delete_and_historical_meal_snapshot_isolation(database_session) -> None:
    service, _ = _service(database_session)
    owner = _user("recipe-service-delete-owner@example.com")
    other = _user("recipe-service-delete-other@example.com")
    analysis_session, component_id = _create_session(database_session, owner)
    database_session.add(other)
    food = Food(
        name="Reference rice", normalized_name="reference rice",
        calories_per_100g=Decimal("130.00"), protein_g_per_100g=Decimal("2.700"),
        carbohydrates_g_per_100g=Decimal("28.000"), fat_g_per_100g=Decimal("0.300"),
        fiber_g_per_100g=Decimal("0.400"), source_name="USDA", source_type="USDA", is_verified=True,
    )
    database_session.add(food)
    database_session.flush()
    snapshot = {"version": 1, "dish_name": "Historical Sinigang", "ingredients": []}
    meal = Meal(
        user_id=owner.id, total_calories=Decimal("130.000"), total_protein_g=Decimal("2.700"),
        total_carbohydrates_g=Decimal("28.000"), total_fat_g=Decimal("0.300"), total_fiber_g=Decimal("0.400"),
        items=[MealItem(
            food_id=food.id, weight_grams=Decimal("100.000"), calculated_calories=Decimal("130.000"),
            calculated_protein_g=Decimal("2.700"), calculated_carbohydrates_g=Decimal("28.000"),
            calculated_fat_g=Decimal("0.300"), calculated_fiber_g=Decimal("0.400"),
            food_name_snapshot="Reference rice", food_normalized_name_snapshot="reference rice",
            composite_provenance_snapshot=snapshot,
        )],
    )
    database_session.add(meal)
    database_session.flush()
    recipe = service.save_from_analysis_component(
        user_id=owner.id, analysis_session_id=analysis_session.id, component_id=component_id
    )

    assert service.get_for_user(recipe.id, owner.id).id == recipe.id
    with pytest.raises(UserRecipeNotFoundError):
        service.get_for_user(recipe.id, other.id)
    with pytest.raises(UserRecipeNotFoundError):
        service.delete_for_user(recipe.id, other.id)

    service.delete_for_user(recipe.id, owner.id)
    database_session.refresh(meal.items[0])
    assert meal.items[0].composite_provenance_snapshot == snapshot
    with pytest.raises(UserRecipeNotFoundError):
        service.get_for_user(recipe.id, owner.id)
