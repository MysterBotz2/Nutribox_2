from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"


class NutritionGoal(str, Enum):
    MAINTAIN_WEIGHT = "maintain_weight"
    LOSE_WEIGHT = "lose_weight"
    GAIN_WEIGHT = "gain_weight"
    GENERAL_HEALTH = "general_health"


class NutritionProfileUpdateRequest(BaseModel):
    """Full-replacement profile input; omitted scalar fields are cleared."""

    model_config = ConfigDict(str_strip_whitespace=True)

    age: int | None = Field(default=None, ge=0, le=130)
    height_cm: Decimal | None = Field(default=None, gt=0, le=300, allow_inf_nan=False)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=500, allow_inf_nan=False)
    activity_level: ActivityLevel | None = None
    nutrition_goal: NutritionGoal | None = None
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=20)
    allergies: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("dietary_restrictions", "allergies")
    @classmethod
    def validate_labels(cls, values: list[str]) -> list[str]:
        cleaned = [" ".join(value.split()) for value in values]
        if any(not value or len(value) > 100 for value in cleaned):
            raise ValueError("Profile labels must be between 1 and 100 characters.")
        return cleaned

class NutritionProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    age: int | None
    height_cm: Decimal | None
    weight_kg: Decimal | None
    activity_level: ActivityLevel | None
    nutrition_goal: NutritionGoal | None
    dietary_restrictions: list[str]
    allergies: list[str]
    created_at: datetime
    updated_at: datetime
