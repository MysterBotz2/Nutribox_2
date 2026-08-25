from decimal import Decimal
from enum import Enum
from typing import Any

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


class NutritionSourceCategory(str, Enum):
    """Approved nutrition provenance categories exposed to API clients."""

    CANTEEN_RECIPE = "canteen_recipe"
    LOCAL_DATABASE = "local_database"
    USDA = "USDA"
    AI_ESTIMATE = "AI_estimate"
    AI_RECIPE_ESTIMATE = "ai_recipe_estimate"


class AdditionalNutrientValues(BaseModel):
    """Nullable V2 nutrients in their canonical units; ``None`` means unknown."""

    saturated_fat_g: Decimal | None = None
    sugars_g: Decimal | None = None
    sodium_mg: Decimal | None = None
    cholesterol_mg: Decimal | None = None
    omega_3_g: Decimal | None = None
    omega_6_g: Decimal | None = None
    calcium_mg: Decimal | None = None
    potassium_mg: Decimal | None = None
    zinc_mg: Decimal | None = None
    iron_mg: Decimal | None = None
    magnesium_mg: Decimal | None = None
    vitamin_a_mcg_rae: Decimal | None = None
    vitamin_b12_mcg: Decimal | None = None
    vitamin_c_mg: Decimal | None = None
    vitamin_d_mcg: Decimal | None = None
    folate_mcg_dfe: Decimal | None = None


class V2NutrientValues(NutrientValues):
    """Stable v1 nutrient values plus nullable additive V2 nutrient values."""

    saturated_fat_g: Decimal | None = None
    sugars_g: Decimal | None = None
    sodium_mg: Decimal | None = None
    cholesterol_mg: Decimal | None = None
    omega_3_g: Decimal | None = None
    omega_6_g: Decimal | None = None
    calcium_mg: Decimal | None = None
    potassium_mg: Decimal | None = None
    zinc_mg: Decimal | None = None
    iron_mg: Decimal | None = None
    magnesium_mg: Decimal | None = None
    vitamin_a_mcg_rae: Decimal | None = None
    vitamin_b12_mcg: Decimal | None = None
    vitamin_c_mg: Decimal | None = None
    vitamin_d_mcg: Decimal | None = None
    folate_mcg_dfe: Decimal | None = None


class NutritionPer100g(V2NutrientValues):
    """Nutrient reference values, all expressed per 100 grams."""


class PortionNutrition(V2NutrientValues):
    """Deterministically calculated nutrient values for one measured portion."""

    @classmethod
    def from_extended(cls, nutrition: Any) -> "PortionNutrition":
        return cls(**nutrition.__dict__)


class FoodSource(BaseModel):
    """Traceability metadata for a nutrition reference record."""

    name: str
    reference: str | None
    verified: bool
    category: NutritionSourceCategory | None = None


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
                saturated_fat_g=food.saturated_fat_g_per_100g,
                sugars_g=food.sugars_g_per_100g,
                sodium_mg=food.sodium_mg_per_100g,
                cholesterol_mg=food.cholesterol_mg_per_100g,
                omega_3_g=food.omega_3_g_per_100g,
                omega_6_g=food.omega_6_g_per_100g,
                calcium_mg=food.calcium_mg_per_100g,
                potassium_mg=food.potassium_mg_per_100g,
                zinc_mg=food.zinc_mg_per_100g,
                iron_mg=food.iron_mg_per_100g,
                magnesium_mg=food.magnesium_mg_per_100g,
                vitamin_a_mcg_rae=food.vitamin_a_mcg_rae_per_100g,
                vitamin_b12_mcg=food.vitamin_b12_mcg_per_100g,
                vitamin_c_mg=food.vitamin_c_mg_per_100g,
                vitamin_d_mcg=food.vitamin_d_mcg_per_100g,
                folate_mcg_dfe=food.folate_mcg_dfe_per_100g,
            ),
            source=FoodSource(
                name=food.source_name,
                reference=food.source_reference,
                verified=food.is_verified,
                category=food.source_type,
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

    id: int | None
    name: str


class PortionCalculationResponse(BaseModel):
    """A deterministic calculation result for a food reference and portion."""

    food: CalculatedFood
    weight_grams: Decimal
    nutrition: PortionNutrition
