from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class WeightSource(str, Enum):
    MANUAL = "manual"
    MEASURED = "measured"
    AI_ESTIMATE = "ai_estimate"
    USER_CONFIRMED = "user_confirmed"


class ComponentResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    REQUIRES_FOOD_SELECTION = "requires_food_selection"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"
    REQUIRES_INGREDIENT_VERIFICATION = "requires_ingredient_verification"
    REQUIRES_RECIPE_CONFIRMATION = "requires_recipe_confirmation"


class IngredientResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    REQUIRES_FOOD_SELECTION = "requires_food_selection"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"


class SuggestedIngredient(BaseModel):
    ingredient_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=160)
    suggested_proportion: Decimal = Field(ge=0)
    ingredient_source: Literal["ai_estimate", "user_confirmed"] = "ai_estimate"
    included: bool = True
    weight_grams: Decimal | None = Field(default=None, gt=0)
    weight_source: WeightSource = WeightSource.AI_ESTIMATE
    resolution_status: IngredientResolutionStatus = IngredientResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND
    candidates: list[dict[str, str]] = Field(default_factory=list)
    resolved_reference: str | None = None
    nutrition_source: str | None = None
    nutrition: dict[str, str | None] | None = None
    food_id: int | None = None
    recipe_derived: bool = False


class PersonalRecipeMatch(BaseModel):
    recipe_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    source: Literal["personal"] = "personal"


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
    ingredient_source: Literal["ai_estimate", "user_confirmed"] = "ai_estimate"
    weight_source: WeightSource = WeightSource.AI_ESTIMATE

    @field_validator("raw_estimated_proportion", "normalized_proportion", "estimated_weight_grams")
    @classmethod
    def finite_decimal(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Composite ingredient decimals must be finite.")
        return value


class CompositeProvenanceSnapshot(BaseModel):
    """Versioned snapshot for a top-level dish estimated from internal composition."""

    version: Literal[1] = 1
    estimation_method: Literal["ai_recipe_estimate", "personal_recipe"] = "ai_recipe_estimate"
    composition_source: Literal["ai_estimate", "user_confirmed", "personal_recipe"] = "ai_estimate"
    recipe_id: int | None = Field(default=None, gt=0)
    recipe_name_snapshot: str | None = Field(default=None, min_length=1, max_length=160)
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

    @model_validator(mode="after")
    def personal_recipe_identity_is_complete(self):
        if self.composition_source == "personal_recipe":
            if self.estimation_method != "personal_recipe" or self.recipe_id is None or self.recipe_name_snapshot is None:
                raise ValueError("Personal recipe provenance requires recipe identity.")
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
    suggested_ingredients: list[SuggestedIngredient] = Field(default_factory=list)
    recipe_matches: list[PersonalRecipeMatch] = Field(default_factory=list)

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
