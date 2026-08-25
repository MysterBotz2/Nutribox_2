from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class WeightSource(str, Enum):
    MANUAL = "manual"
    MEASURED = "measured"
    AI_ESTIMATE = "ai_estimate"


class ComponentResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    REQUIRES_FOOD_SELECTION = "requires_food_selection"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"


class CompositeIngredientSnapshot(BaseModel):
    """Immutable, reference-backed evidence for one estimated dish ingredient."""

    ingredient_name: str = Field(min_length=1, max_length=160)
    raw_estimated_proportion: Decimal
    normalized_proportion: Decimal
    estimated_weight_grams: Decimal = Field(gt=0)
    nutrition_source: str = Field(min_length=1, max_length=32)
    source_reference_id: str = Field(min_length=1)
    reference_name: str = Field(min_length=1, max_length=160)
    nutrition: dict[str, str | None]

    @field_validator("raw_estimated_proportion", "normalized_proportion", "estimated_weight_grams")
    @classmethod
    def finite_decimal(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Composite ingredient decimals must be finite.")
        return value


class CompositeProvenanceSnapshot(BaseModel):
    """Versioned snapshot for a top-level dish estimated from internal composition."""

    version: Literal[1] = 1
    estimation_method: Literal["ai_recipe_estimate"] = "ai_recipe_estimate"
    dish_name: str = Field(min_length=1, max_length=160)
    dish_weight_grams: Decimal = Field(gt=0)
    ingredients: list[CompositeIngredientSnapshot] = Field(min_length=1, max_length=50)

    @field_validator("dish_weight_grams")
    @classmethod
    def finite_dish_weight(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Composite dish weight must be finite.")
        return value

    @model_validator(mode="after")
    def ingredient_weights_reconcile(self):
        if sum((ingredient.estimated_weight_grams for ingredient in self.ingredients), Decimal("0")) != self.dish_weight_grams:
            raise ValueError("Composite ingredient weights must equal the dish weight exactly.")
        return self


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
    composite_provenance_snapshot: CompositeProvenanceSnapshot | None = None

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
