from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.nutrition import PortionNutrition


class LeftoverScanCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_session_id: int = Field(gt=0)


class LeftoverScanComparisonNutrient(str, Enum):
    CALORIES = "calories"
    PROTEIN_G = "protein_g"
    CARBOHYDRATES_G = "carbohydrates_g"
    FAT_G = "fat_g"
    FIBER_G = "fiber_g"
    SATURATED_FAT_G = "saturated_fat_g"
    SUGARS_G = "sugars_g"
    SODIUM_MG = "sodium_mg"
    CHOLESTEROL_MG = "cholesterol_mg"
    OMEGA_3_G = "omega_3_g"
    OMEGA_6_G = "omega_6_g"
    CALCIUM_MG = "calcium_mg"
    POTASSIUM_MG = "potassium_mg"
    ZINC_MG = "zinc_mg"
    IRON_MG = "iron_mg"
    MAGNESIUM_MG = "magnesium_mg"
    PHOSPHORUS_MG = "phosphorus_mg"
    VITAMIN_B6_MG = "vitamin_b6_mg"
    NIACIN_MG = "niacin_mg"
    VITAMIN_A_MCG_RAE = "vitamin_a_mcg_rae"
    VITAMIN_B12_MCG = "vitamin_b12_mcg"
    VITAMIN_C_MG = "vitamin_c_mg"
    VITAMIN_D_MCG = "vitamin_d_mcg"
    FOLATE_MCG_DFE = "folate_mcg_dfe"


class LeftoverScanComparisonWarning(BaseModel):
    nutrient: LeftoverScanComparisonNutrient
    code: Literal["remaining_exceeds_original"]


class LeftoverScanResponse(BaseModel):
    id: int
    meal_id: int
    analysis_session_id: int
    original_weight_grams: Decimal
    remaining_weight_grams: Decimal
    consumed_weight_grams: Decimal
    consumed_portion_percentage: Decimal
    remaining_nutrition: PortionNutrition
    estimated_consumed_nutrition: PortionNutrition
    comparison_warnings: list[LeftoverScanComparisonWarning]
    created_at: datetime
