from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import RecognizedFood
from app.schemas.nutrition import (
    AdditionalNutrientValues,
    CalculatedFood,
    NutrientValues,
    PortionNutrition,
)
from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS


class MealAnalysisStatus(str, Enum):
    CALCULATED = "calculated"
    FOOD_NOT_RECOGNIZED = "food_not_recognized"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"
    REQUIRES_FOOD_SELECTION = "requires_food_selection"


class MealAnalysisBase(BaseModel):
    recognized_foods: list[RecognizedFood]
    recognition_source: str


class CalculatedMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.CALCULATED]
    food: CalculatedFood
    weight_grams: Decimal
    nutrition: PortionNutrition
    weight_source: Literal["manual"]


class FoodNotRecognizedMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.FOOD_NOT_RECOGNIZED]


class NutritionReferenceNotFoundMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND]


class RequiresFoodSelectionMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.REQUIRES_FOOD_SELECTION]


MealAnalysisResponse = Annotated[
    CalculatedMealAnalysis
    | FoodNotRecognizedMealAnalysis
    | NutritionReferenceNotFoundMealAnalysis
    | RequiresFoodSelectionMealAnalysis,
    Field(discriminator="status"),
]


class MealItemCreateRequest(BaseModel):
    food_id: int = Field(gt=0)
    weight_grams: Decimal = Field(gt=0, le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS, allow_inf_nan=False)


class MealCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MealItemCreateRequest] = Field(min_length=1, max_length=50)


class MealItemResponse(BaseModel):
    id: int
    food: CalculatedFood
    weight_grams: Decimal
    nutrition: PortionNutrition
    nutrition_source: "MealItemNutritionSource | None" = None


class MealItemNutritionSource(BaseModel):
    """Immutable provenance snapshot for a saved meal item."""

    category: str | None
    name: str | None
    reference: str | None
    is_estimated: bool | None


class MealListItemResponse(BaseModel):
    """Legacy-compatible compact item representation for paginated meal lists."""

    id: int
    food: CalculatedFood
    weight_grams: Decimal
    nutrition: NutrientValues


class MealTotals(PortionNutrition):
    pass


class MealResponse(BaseModel):
    id: int
    recorded_at: datetime
    items: list[MealItemResponse]
    totals: MealTotals
    additional_totals: AdditionalNutrientValues


class MealListItem(BaseModel):
    """Legacy-compatible meal representation that avoids expanded item payloads."""

    id: int
    recorded_at: datetime
    items: list[MealListItemResponse]
    totals: MealTotals


class MealListResponse(BaseModel):
    meals: list[MealListItem]
    limit: int
    offset: int
