from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.food import Food, NUTRITION_SOURCE_TYPES
from app.models.meal import Meal, MealItem


def make_food(name: str = "V2 Nutrition Test Food") -> Food:
    return Food(
        name=name,
        category="test",
        calories_per_100g=Decimal("100.00"),
        protein_g_per_100g=Decimal("10.000"),
        carbohydrates_g_per_100g=Decimal("20.000"),
        fat_g_per_100g=Decimal("3.000"),
        fiber_g_per_100g=Decimal("2.000"),
        source_name="Synthetic test source",
        is_verified=False,
    )


def test_food_keeps_unknown_nutrients_null_and_explicit_zeroes(database_session: Session) -> None:
    food = make_food()
    food.sodium_mg_per_100g = Decimal("0.000")
    food.vitamin_c_mg_per_100g = Decimal("0.000")
    database_session.add(food)
    database_session.flush()
    database_session.refresh(food)

    assert food.saturated_fat_g_per_100g is None
    assert food.omega_3_g_per_100g is None
    assert food.vitamin_b12_mcg_per_100g is None
    assert food.sodium_mg_per_100g == Decimal("0.000")
    assert food.vitamin_c_mg_per_100g == Decimal("0.000")


@pytest.mark.parametrize("source_type", NUTRITION_SOURCE_TYPES)
def test_food_accepts_each_canonical_source_type(
    database_session: Session, source_type: str
) -> None:
    food = make_food(f"V2 Source {source_type}")
    food.source_type = source_type
    database_session.add(food)
    database_session.flush()

    assert food.source_type == source_type


def test_food_rejects_negative_new_nutrient_values(database_session: Session) -> None:
    food = make_food()
    food.sodium_mg_per_100g = Decimal("-0.001")
    database_session.add(food)

    with pytest.raises(IntegrityError):
        database_session.flush()


def test_food_rejects_unknown_source_type(database_session: Session) -> None:
    food = make_food()
    food.source_type = "vendor_specific_source"
    database_session.add(food)

    with pytest.raises(IntegrityError):
        database_session.flush()


def test_meal_item_persists_extended_snapshot_and_provenance(database_session: Session) -> None:
    food = make_food()
    database_session.add(food)
    database_session.flush()

    item = MealItem(
        food_id=food.id,
        weight_grams=Decimal("100.000"),
        calculated_calories=Decimal("100.000"),
        calculated_protein_g=Decimal("10.000"),
        calculated_carbohydrates_g=Decimal("20.000"),
        calculated_fat_g=Decimal("3.000"),
        calculated_fiber_g=Decimal("2.000"),
        calculated_saturated_fat_g=Decimal("1.000"),
        calculated_sodium_mg=Decimal("250.000"),
        calculated_vitamin_b12_mcg=Decimal("0.500"),
        food_name_snapshot=food.name,
        food_normalized_name_snapshot=food.normalized_name,
        nutrition_source_type="USDA",
        nutrition_source_name_snapshot="USDA FoodData Central",
        nutrition_source_reference_snapshot="fdcId:12345",
        nutrition_is_estimated=False,
    )
    meal = Meal(
        total_calories=Decimal("100.000"),
        total_protein_g=Decimal("10.000"),
        total_carbohydrates_g=Decimal("20.000"),
        total_fat_g=Decimal("3.000"),
        total_fiber_g=Decimal("2.000"),
        items=[item],
    )
    database_session.add(meal)
    database_session.flush()
    database_session.refresh(item)

    assert item.calculated_saturated_fat_g == Decimal("1.000")
    assert item.calculated_sodium_mg == Decimal("250.000")
    assert item.calculated_vitamin_b12_mcg == Decimal("0.500")
    assert item.calculated_cholesterol_mg is None
    assert item.nutrition_source_type == "USDA"
    assert item.nutrition_source_name_snapshot == "USDA FoodData Central"
    assert item.nutrition_source_reference_snapshot == "fdcId:12345"
    assert item.nutrition_is_estimated is False
