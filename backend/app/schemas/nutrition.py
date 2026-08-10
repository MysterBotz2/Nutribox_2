from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.food import Food


class NutritionPer100g(BaseModel):
    """Nutrient reference values, all expressed per 100 grams."""

    calories: Decimal
    protein_g: Decimal
    carbohydrates_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal


class FoodSource(BaseModel):
    """Traceability metadata for a nutrition reference record."""

    name: str
    reference: str | None
    verified: bool


class FoodResponse(BaseModel):
    """Structured API representation of one canonical food record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    normalized_name: str
    category: str | None
    nutrition_per_100g: NutritionPer100g
    source: FoodSource

    @classmethod
    def from_food(cls, food: Food) -> "FoodResponse":
        return cls(
            id=food.id,
            name=food.name,
            normalized_name=food.normalized_name,
            category=food.category,
            nutrition_per_100g=NutritionPer100g(
                calories=food.calories_per_100g,
                protein_g=food.protein_g_per_100g,
                carbohydrates_g=food.carbohydrates_g_per_100g,
                fat_g=food.fat_g_per_100g,
                fiber_g=food.fiber_g_per_100g,
            ),
            source=FoodSource(
                name=food.source_name,
                reference=food.source_reference,
                verified=food.is_verified,
            ),
        )


class FoodListResponse(BaseModel):
    """Collection response for food reference searches."""

    foods: list[FoodResponse]
