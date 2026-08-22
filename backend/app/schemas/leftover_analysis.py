from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class LeftoverNutrition(BaseModel):
    calories: Decimal
    protein_g: Decimal
    carbohydrates_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal


class LeftoverAnalysisProvenance(BaseModel):
    source: str
    recognized_food_name: str | None
    source_reference: str | None


class LeftoverAnalysisResponse(BaseModel):
    id: int
    meal_id: int
    leftover_weight_grams: Decimal
    initial_nutrition: LeftoverNutrition
    leftover_nutrition: LeftoverNutrition
    consumed_nutrition: LeftoverNutrition
    provenance: LeftoverAnalysisProvenance
    created_at: datetime
