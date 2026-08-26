from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.user import User
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    CompositeIngredientSnapshot,
    CompositeProvenanceSnapshot,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
    WeightSource,
)
from app.services.meal_analysis_session_service import MealAnalysisSessionService
from tests.conftest import register_and_login


def _session_state(*, status: ComponentResolutionStatus = ComponentResolutionStatus.RESOLVED, composite: bool = True, confirmed: bool = True):
    component_id = str(uuid4())
    ingredients = [
        CompositeIngredientSnapshot(
            ingredient_name="Pork", raw_estimated_proportion=Decimal("0.600"),
            normalized_proportion=Decimal("0.600"), estimated_weight_grams=Decimal("120.000"),
            nutrition_source="USDA", source_reference_id="fdcId:111", reference_name="Pork, cooked",
            nutrition={"calories": "120.000"}, ingredient_source="user_confirmed",
            weight_source=WeightSource.USER_CONFIRMED,
        ),
        CompositeIngredientSnapshot(
            ingredient_name="Broth", raw_estimated_proportion=Decimal("0.400"),
            normalized_proportion=Decimal("0.400"), estimated_weight_grams=Decimal("80.000"),
            nutrition_source="local_database", source_reference_id="food:42", reference_name="Broth",
            nutrition={"calories": "20.000"}, ingredient_source="user_confirmed",
            weight_source=WeightSource.AI_ESTIMATE,
        ),
    ]
    provenance = (
        CompositeProvenanceSnapshot(
            dish_name="Pork Sinigang", dish_weight_grams=Decimal("200.000"),
            ingredients=ingredients, composition_source="user_confirmed" if confirmed else "ai_estimate",
        )
        if composite else None
    )
    component = MealAnalysisSessionComponent(
        component_id=component_id, recognized_name="Pork Sinigang",
        raw_estimated_proportion=Decimal("1"), normalized_proportion=Decimal("1"),
        estimated_weight_grams=Decimal("200.000"), resolution_status=status,
        nutrition_source="ai_recipe_estimate" if composite else "USDA",
        nutrition={"calories": "140.000"}, composite_provenance_snapshot=provenance,
    )
    return MealAnalysisSessionState(
        measured_weight_grams=Decimal("200.000"), components=[component]
    ), component_id


def _analysis_session(database_session, user_id: int, **kwargs):
    state, component_id = _session_state(**kwargs)
    service = MealAnalysisSessionService(MealAnalysisSessionRepository(database_session))
    item = service.create_session(user_id, state, "calculated")
    return item, component_id


def _save_path(session_id: int, component_id: str) -> str:
    return f"/api/meals/analysis-sessions/{session_id}/components/{component_id}/save-recipe"


def test_save_recipe_is_authenticated_and_returns_trusted_recipe(client, database_session, jwt_configuration) -> None:
    user, headers = register_and_login(client, "recipe-api-owner@example.com")
    item, component_id = _analysis_session(database_session, user["id"])

    assert client.post(_save_path(item.id, component_id)).status_code == 401
    response = client.post(
        _save_path(item.id, component_id), json={"name": "My Pork Sinigang"}, headers=headers
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "My Pork Sinigang"
    assert payload["source_type"] == "user_confirmed"
    assert payload["ingredients"] == [
        {
            "name": "Pork", "normalized_proportion": "0.600000000",
            "nutrition_source": "USDA", "resolved_reference": "fdcId:111",
            "ingredient_source": "user_confirmed", "weight_source": "user_confirmed",
        },
        {
            "name": "Broth", "normalized_proportion": "0.400000000",
            "nutrition_source": "local_database", "resolved_reference": "food:42",
            "ingredient_source": "user_confirmed", "weight_source": "ai_estimate",
        },
    ]
    database_session.refresh(item)
    assert item.consumed_at is None


def test_save_recipe_maps_invalid_session_states_safely(client, database_session, jwt_configuration) -> None:
    user, headers = register_and_login(client, "recipe-api-invalid@example.com")
    invalid, invalid_component = _analysis_session(
        database_session, user["id"], status=ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION
    )
    direct, direct_component = _analysis_session(database_session, user["id"], composite=False)
    unconfirmed, unconfirmed_component = _analysis_session(database_session, user["id"], confirmed=False)
    expired, expired_component = _analysis_session(database_session, user["id"])
    consumed, consumed_component = _analysis_session(database_session, user["id"])
    expired.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    consumed.consumed_at = datetime.now(timezone.utc)
    database_session.flush()

    for item, component_id in ((invalid, invalid_component), (direct, direct_component), (unconfirmed, unconfirmed_component)):
        response = client.post(_save_path(item.id, component_id), headers=headers)
        assert response.status_code == 409
        assert response.json() == {"detail": "Analysis component is not eligible to save as a personal recipe."}
    assert client.post(_save_path(expired.id, expired_component), headers=headers).status_code == 410
    assert client.post(_save_path(consumed.id, consumed_component), headers=headers).status_code == 409


def test_recipe_list_detail_and_delete_are_owner_scoped(client, database_session, jwt_configuration) -> None:
    owner, owner_headers = register_and_login(client, "recipe-api-list-owner@example.com")
    other, other_headers = register_and_login(client, "recipe-api-list-other@example.com")
    assert client.get("/api/users/me/recipes", headers=other_headers).json() == {"recipes": []}
    item, component_id = _analysis_session(database_session, owner["id"])
    created = client.post(_save_path(item.id, component_id), headers=owner_headers)
    recipe_id = created.json()["id"]

    listed = client.get("/api/users/me/recipes", headers=owner_headers)
    assert listed.status_code == 200
    assert [recipe["id"] for recipe in listed.json()["recipes"]] == [recipe_id]
    assert client.get(f"/api/users/me/recipes/{recipe_id}", headers=owner_headers).status_code == 200
    assert client.get(f"/api/users/me/recipes/{recipe_id}", headers=other_headers).status_code == 404
    assert client.get("/api/users/me/recipes/999999", headers=owner_headers).status_code == 404
    assert client.delete(f"/api/users/me/recipes/{recipe_id}", headers=other_headers).status_code == 404
    assert client.delete(f"/api/users/me/recipes/{recipe_id}", headers=owner_headers).status_code == 204
    assert client.get(f"/api/users/me/recipes/{recipe_id}", headers=owner_headers).status_code == 404


def test_recipe_delete_preserves_food_and_meal_history(client, database_session, jwt_configuration) -> None:
    user, headers = register_and_login(client, "recipe-api-history@example.com")
    food = Food(
        name="Reference rice", normalized_name="reference rice", calories_per_100g=Decimal("130.00"),
        protein_g_per_100g=Decimal("2.700"), carbohydrates_g_per_100g=Decimal("28.000"),
        fat_g_per_100g=Decimal("0.300"), fiber_g_per_100g=Decimal("0.400"),
        source_name="USDA", source_type="USDA", is_verified=True,
    )
    database_session.add(food)
    database_session.flush()
    snapshot = {"version": 1, "dish_name": "Historical Sinigang", "ingredients": []}
    meal = Meal(
        user_id=user["id"], total_calories=Decimal("130.000"), total_protein_g=Decimal("2.700"),
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
    item, component_id = _analysis_session(database_session, user["id"])
    database_session.flush()
    recipe_id = client.post(_save_path(item.id, component_id), headers=headers).json()["id"]

    assert client.delete(f"/api/users/me/recipes/{recipe_id}", headers=headers).status_code == 204
    database_session.refresh(meal.items[0])
    assert database_session.get(Food, food.id) is not None
    assert database_session.get(Meal, meal.id) is not None
    assert meal.items[0].composite_provenance_snapshot == snapshot
