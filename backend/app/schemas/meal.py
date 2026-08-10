from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.ai import RecognizedFood
from app.schemas.nutrition import CalculatedFood, PortionNutrition


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
