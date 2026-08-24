from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class WeightSource(str, Enum):
    MANUAL = "manual"
    MEASURED = "measured"
    AI_ESTIMATE = "ai_estimate"


class ComponentResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    REQUIRES_FOOD_SELECTION = "requires_food_selection"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"


class MealAnalysisSessionComponent(BaseModel):
    component_id: UUID = Field(default_factory=uuid4)
    recognized_name: str = Field(min_length=1, max_length=160)
    raw_estimated_proportion: Decimal
    normalized_proportion: Decimal
    estimated_weight_grams: Decimal
    weight_source: WeightSource = WeightSource.AI_ESTIMATE
    resolution_status: ComponentResolutionStatus
    candidates: list[dict[str, str]] = Field(default_factory=list)
    resolved_reference: str | None = None
    nutrition_source: str | None = None
    nutrition: dict[str, str | None] | None = None

    @field_validator("raw_estimated_proportion", "normalized_proportion", "estimated_weight_grams")
    @classmethod
    def finite_decimal(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Session decimal values must be finite.")
        return value


class MealAnalysisSessionState(BaseModel):
    version: Literal[1] = 1
    measured_weight_grams: Decimal
    components: list[MealAnalysisSessionComponent] = Field(min_length=1, max_length=50)

    @field_validator("measured_weight_grams")
    @classmethod
    def finite_weight(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Measured meal weight must be finite.")
        return value
