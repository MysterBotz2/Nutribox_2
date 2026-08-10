from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.models.food import Food


class NutrientValues(BaseModel):
    """A shared collection of nutrient values expressed in a stated context."""

    calories: Decimal
    protein_g: Decimal
    carbohydrates_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal


class NutritionPer100g(NutrientValues):
    """Nutrient reference values, all expressed per 100 grams."""


class PortionNutrition(NutrientValues):
    """Deterministically calculated nutrient values for one measured portion."""


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


class PortionCalculationRequest(BaseModel):
    """A food reference identifier and measured portion weight."""

    food_id: int = Field(gt=0)
    weight_grams: Decimal = Field(
        ge=0,
        le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS,
        allow_inf_nan=False,
        description="Measured portion weight in grams, from 0 to 5000.",
    )


class CalculatedFood(BaseModel):
    """The canonical food reference used for a portion calculation."""

    id: int
    name: str


class PortionCalculationResponse(BaseModel):
    """A deterministic calculation result for a food reference and portion."""

    food: CalculatedFood
    weight_grams: Decimal
    nutrition: PortionNutrition
