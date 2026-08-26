from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.food import Food
from app.models.user_recipe import UserRecipe, UserRecipeIngredient
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
    PersonalRecipeMatch,
)
from app.services.meal_analysis_session_service import MealAnalysisSessionService
from tests.conftest import register_and_login


def _food(name: str, calories: str) -> Food:
    return Food(
        name=name, normalized_name=name.casefold(), calories_per_100g=Decimal(calories),
        protein_g_per_100g=Decimal("10"), carbohydrates_g_per_100g=Decimal("20"),
        fat_g_per_100g=Decimal("3"), fiber_g_per_100g=Decimal("2"),
        source_name="Local reference", source_type="local_database", is_verified=True,
    )


def _recipe(user_id: int, pork: Food, broth: Food) -> UserRecipe:
    return UserRecipe(
        user_id=user_id, name="Pork Sinigang", normalized_name="pork sinigang",
        ingredients=[
            UserRecipeIngredient(position=1, name_snapshot="Pork", normalized_name="pork", normalized_proportion=Decimal("0.600000000"), nutrition_source_type="local_database", resolved_reference=f"food:{pork.id}", ingredient_source="user_confirmed", weight_source="user_confirmed"),
            UserRecipeIngredient(position=2, name_snapshot="Broth", normalized_name="broth", normalized_proportion=Decimal("0.400000000"), nutrition_source_type="local_database", resolved_reference=f"food:{broth.id}", ingredient_source="user_confirmed", weight_source="ai_estimate"),
        ],
    )


def _session(database_session, user_id: int, recipe: UserRecipe):
    component = MealAnalysisSessionComponent(
        component_id=uuid4(), recognized_name="Pork Sinigang", raw_estimated_proportion=Decimal("1"),
        normalized_proportion=Decimal("1"), estimated_weight_grams=Decimal("275.000"),
        resolution_status=ComponentResolutionStatus.REQUIRES_RECIPE_CONFIRMATION,
        recipe_matches=[PersonalRecipeMatch(recipe_id=recipe.id, name=recipe.name)],
    )
    item = MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)).create_session(
        user_id, MealAnalysisSessionState(measured_weight_grams=Decimal("275.000"), components=[component]), "requires_recipe_confirmation"
    )
    return item, str(component.component_id)


def test_recipe_reuse_api_use_review_and_lifecycle_security(client, database_session, jwt_configuration) -> None:
    owner, owner_headers = register_and_login(client, "reuse-api-owner@example.com")
    _, other_headers = register_and_login(client, "reuse-api-other@example.com")
    pork, broth = _food("Pork", "200"), _food("Broth", "10")
    database_session.add_all([pork, broth]); database_session.flush()
    recipe = _recipe(owner["id"], pork, broth); database_session.add(recipe); database_session.flush()
    item, component_id = _session(database_session, owner["id"], recipe)
    path = f"/api/meals/analysis-sessions/{item.id}/components/{component_id}"

    assert client.post(f"{path}/use-recipe", json={"recipe_id": recipe.id}, headers=other_headers).status_code == 404
    used = client.post(f"{path}/use-recipe", json={"recipe_id": recipe.id}, headers=owner_headers)
    assert used.status_code == 200
    assert used.json()["status"] == "calculated"
    assert used.json()["components"][0]["composite_estimation"] is True
    database_session.refresh(item)
    assert item.consumed_at is None

    review_item, review_component_id = _session(database_session, owner["id"], recipe)
    reviewed = client.post(
        f"/api/meals/analysis-sessions/{review_item.id}/components/{review_component_id}/review-recipe",
        json={"recipe_id": recipe.id}, headers=owner_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "requires_ingredient_verification"
    assert all(item["recipe_derived"] for item in reviewed.json()["components"][0]["suggested_ingredients"])

    expired, expired_component_id = _session(database_session, owner["id"], recipe)
    expired.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1); database_session.flush()
    assert client.post(f"/api/meals/analysis-sessions/{expired.id}/components/{expired_component_id}/use-recipe", json={"recipe_id": recipe.id}, headers=owner_headers).status_code == 410
