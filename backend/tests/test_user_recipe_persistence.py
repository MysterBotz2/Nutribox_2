from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.user import User
from app.models.user_recipe import UserRecipe, UserRecipeIngredient


def _user(email: str) -> User:
    return User(
        email=email,
        password_hash="not-a-real-password",
        first_name="Recipe",
        last_name="Owner",
    )


def _ingredient(position: int, name: str, proportion: str) -> UserRecipeIngredient:
    return UserRecipeIngredient(
        position=position,
        name_snapshot=name,
        normalized_name="ignored-by-normalization-hook",
        normalized_proportion=Decimal(proportion),
        nutrition_source_type="USDA",
        resolved_reference=f"fdcId:{169712 + position}",
        ingredient_source="user_confirmed",
        weight_source="user_confirmed",
    )


def _food() -> Food:
    return Food(
        name="Reference rice",
        normalized_name="reference rice",
        calories_per_100g=Decimal("130.00"),
        protein_g_per_100g=Decimal("2.700"),
        carbohydrates_g_per_100g=Decimal("28.000"),
        fat_g_per_100g=Decimal("0.300"),
        fiber_g_per_100g=Decimal("0.400"),
        source_name="USDA FoodData Central",
        source_type="USDA",
        is_verified=True,
    )


def test_user_recipe_persists_multiple_ingredients_and_decimal_proportions(database_session) -> None:
    owner = _user("recipe-owner@example.com")
    recipe = UserRecipe(
        user=owner,
        name="  Pork Sinigang  ",
        normalized_name="ignored-by-normalization-hook",
        source_type="user_confirmed",
        ingredients=[
            _ingredient(1, "Pork", "0.400000000"),
            _ingredient(2, "Radish", "0.150000000"),
            _ingredient(3, "Broth", "0.450000000"),
        ],
    )
    database_session.add(recipe)
    database_session.flush()
    database_session.expire_all()

    stored = database_session.scalar(select(UserRecipe).where(UserRecipe.id == recipe.id))
    assert stored is not None
    assert stored.name == "Pork Sinigang"
    assert stored.normalized_name == "pork sinigang"
    assert stored.source_type == "user_confirmed"
    assert [(item.position, item.normalized_proportion) for item in stored.ingredients] == [
        (1, Decimal("0.400000000")),
        (2, Decimal("0.150000000")),
        (3, Decimal("0.450000000")),
    ]
    assert stored.ingredients[0].resolved_reference == "fdcId:169713"


def test_recipe_names_are_not_unique_within_or_across_owners(database_session) -> None:
    first_owner = _user("recipe-first@example.com")
    second_owner = _user("recipe-second@example.com")
    recipes = [
        UserRecipe(user=first_owner, name="Adobo", normalized_name="adobo"),
        UserRecipe(user=first_owner, name="  adobo  ", normalized_name="adobo"),
        UserRecipe(user=second_owner, name="Adobo", normalized_name="adobo"),
    ]
    database_session.add_all(recipes)
    database_session.flush()

    assert len(
        database_session.scalars(
            select(UserRecipe).where(UserRecipe.normalized_name == "adobo")
        ).all()
    ) == 3


def test_deleting_recipe_cascades_ingredients_but_not_food_or_existing_meal_data(database_session) -> None:
    owner = _user("recipe-cascade@example.com")
    food = _food()
    database_session.add(food)
    database_session.flush()
    meal = Meal(
        user=owner,
        total_calories=Decimal("130.000"),
        total_protein_g=Decimal("2.700"),
        total_carbohydrates_g=Decimal("28.000"),
        total_fat_g=Decimal("0.300"),
        total_fiber_g=Decimal("0.400"),
        items=[
            MealItem(
                food_id=food.id,
                weight_grams=Decimal("100.000"),
                calculated_calories=Decimal("130.000"),
                calculated_protein_g=Decimal("2.700"),
                calculated_carbohydrates_g=Decimal("28.000"),
                calculated_fat_g=Decimal("0.300"),
                calculated_fiber_g=Decimal("0.400"),
                food_name_snapshot="Reference rice",
                food_normalized_name_snapshot="reference rice",
            )
        ],
    )
    recipe = UserRecipe(
        user=owner,
        name="Sinigang",
        normalized_name="sinigang",
        ingredients=[_ingredient(1, "Pork", "1.000000000")],
    )
    database_session.add_all([meal, recipe])
    database_session.flush()
    recipe_id = recipe.id
    ingredient_id = recipe.ingredients[0].id
    food_id = food.id
    meal_id = meal.id
    meal_item_id = meal.items[0].id

    database_session.delete(recipe)
    database_session.flush()

    assert database_session.get(UserRecipe, recipe_id) is None
    assert database_session.get(UserRecipeIngredient, ingredient_id) is None
    assert database_session.get(Food, food_id) is not None
    assert database_session.get(Meal, meal_id) is not None
    assert database_session.get(MealItem, meal_item_id) is not None


@pytest.mark.parametrize("proportion", ["0", "-0.001"])
def test_recipe_ingredient_proportion_range_is_enforced_by_database(database_session, proportion: str) -> None:
    recipe = UserRecipe(
        user=_user(f"recipe-invalid-{proportion.replace('-', 'negative')}@example.com"),
        name="Invalid recipe",
        normalized_name="invalid recipe",
        ingredients=[_ingredient(1, "Ingredient", proportion)],
    )
    database_session.add(recipe)

    with pytest.raises(IntegrityError):
        database_session.flush()
    database_session.rollback()


def test_recipe_model_metadata_exposes_migration_tables_indexes_and_constraints() -> None:
    recipe_table = UserRecipe.__table__
    ingredient_table = UserRecipeIngredient.__table__

    assert {"user_recipes", "user_recipe_ingredients"} <= {
        recipe_table.name,
        ingredient_table.name,
    }
    assert "ix_user_recipes_user_id_normalized_name" in {index.name for index in recipe_table.indexes}
    assert "ix_user_recipe_ingredients_recipe_id" in {index.name for index in ingredient_table.indexes}
    assert "ck_user_recipes_source_type" in {constraint.name for constraint in recipe_table.constraints}
    assert "ck_user_recipe_ingredients_proportion_range" in {
        constraint.name for constraint in ingredient_table.constraints
    }
