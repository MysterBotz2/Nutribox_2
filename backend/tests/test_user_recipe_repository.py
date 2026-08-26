from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.models.user import User
from app.models.user_recipe import UserRecipe, UserRecipeIngredient
from app.repositories.user_recipe_repository import UserRecipeRepository


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
        normalized_name=name.casefold(),
        normalized_proportion=Decimal(proportion),
        nutrition_source_type="USDA",
        resolved_reference=f"fdcId:{169712 + position}",
        ingredient_source="user_confirmed",
        weight_source="user_confirmed",
    )


def _recipe(user: User, name: str, *, updated_at: datetime | None = None) -> UserRecipe:
    return UserRecipe(
        user=user,
        name=name,
        normalized_name=name.casefold(),
        updated_at=updated_at,
        ingredients=[
            _ingredient(1, "Pork", "0.400000000"),
            _ingredient(2, "Broth", "0.600000000"),
        ],
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


def test_create_returns_recipe_id_and_persists_ingredient_decimals(database_session) -> None:
    repository = UserRecipeRepository(database_session)
    recipe = repository.create(_recipe(_user("recipe-create@example.com"), "Pork Sinigang"))
    database_session.expire_all()

    stored = repository.get_by_id_for_user(recipe.id, recipe.user_id)
    assert recipe.id is not None
    assert stored is not None
    assert [(item.position, item.normalized_proportion) for item in stored.ingredients] == [
        (1, Decimal("0.400000000")),
        (2, Decimal("0.600000000")),
    ]


def test_owner_scoped_get_list_and_exact_name_lookup_are_deterministic(database_session) -> None:
    repository = UserRecipeRepository(database_session)
    owner = _user("recipe-owner@example.com")
    other_user = _user("recipe-other@example.com")
    now = datetime.now(timezone.utc)
    oldest = repository.create(_recipe(owner, "Adobo", updated_at=now - timedelta(days=2)))
    newest = repository.create(_recipe(owner, " adobo ", updated_at=now - timedelta(days=1)))
    foreign = repository.create(_recipe(other_user, "Adobo", updated_at=now))
    database_session.expire_all()

    assert repository.get_by_id_for_user(newest.id, owner.id) is not None
    assert repository.get_by_id_for_user(foreign.id, owner.id) is None
    assert [recipe.id for recipe in repository.list_for_user(owner.id)] == [newest.id, oldest.id]

    matches = repository.find_by_normalized_name_for_user(owner.id, "adobo")
    assert [recipe.id for recipe in matches] == [newest.id, oldest.id]
    assert all(recipe.ingredients for recipe in matches)


def test_delete_is_owner_scoped_cascades_ingredients_and_preserves_unrelated_records(database_session) -> None:
    repository = UserRecipeRepository(database_session)
    owner = _user("recipe-delete-owner@example.com")
    other_user = _user("recipe-delete-other@example.com")
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
    recipe = repository.create(_recipe(owner, "Sinigang"))
    database_session.add_all([meal, other_user])
    database_session.flush()
    ingredient_ids = [ingredient.id for ingredient in recipe.ingredients]
    food_id, meal_id, meal_item_id = food.id, meal.id, meal.items[0].id

    assert repository.delete_for_user(recipe.id, other_user.id) is False
    assert repository.get_by_id_for_user(recipe.id, owner.id) is not None
    assert repository.delete_for_user(recipe.id, owner.id) is True
    database_session.flush()

    assert repository.get_by_id_for_user(recipe.id, owner.id) is None
    assert database_session.scalars(
        select(UserRecipeIngredient).where(UserRecipeIngredient.id.in_(ingredient_ids))
    ).all() == []
    assert database_session.get(Food, food_id) is not None
    assert database_session.get(Meal, meal_id) is not None
    assert database_session.get(MealItem, meal_item_id) is not None
