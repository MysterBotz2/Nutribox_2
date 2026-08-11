from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.constants import MAXIMUM_TARGET_CALORIES, MAXIMUM_TARGET_NUTRIENT_GRAMS


class TargetSourceType(str, Enum):
    MANUAL = "manual"
    RESEARCHER_ASSIGNED = "researcher_assigned"
    PROFESSIONAL_ASSIGNED = "professional_assigned"


class TargetNutrientValues(BaseModel):
    calories: Decimal | None = Field(
        default=None, gt=0, le=MAXIMUM_TARGET_CALORIES, allow_inf_nan=False
    )
    protein_g: Decimal | None = Field(
        default=None, gt=0, le=MAXIMUM_TARGET_NUTRIENT_GRAMS, allow_inf_nan=False
    )
    carbohydrates_g: Decimal | None = Field(
        default=None, gt=0, le=MAXIMUM_TARGET_NUTRIENT_GRAMS, allow_inf_nan=False
    )
    fat_g: Decimal | None = Field(
        default=None, gt=0, le=MAXIMUM_TARGET_NUTRIENT_GRAMS, allow_inf_nan=False
    )
    fiber_g: Decimal | None = Field(
        default=None, gt=0, le=MAXIMUM_TARGET_NUTRIENT_GRAMS, allow_inf_nan=False
    )


class NutritionTargetUpdateRequest(TargetNutrientValues):
    """Full replacement input for one explicitly configured target set."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: TargetSourceType
    source_reference: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_one_target_value(self) -> "NutritionTargetUpdateRequest":
        if all(
            value is None
            for value in (
                self.calories,
                self.protein_g,
                self.carbohydrates_g,
                self.fat_g,
                self.fiber_g,
            )
        ):
            raise ValueError("At least one nutrition target value must be configured.")
        return self


class NutritionTargetResponse(TargetNutrientValues):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source_type: TargetSourceType
    source_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
