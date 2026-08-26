from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.ai import RecognizedFood
from app.schemas.nutrition import (
    AdditionalNutrientValues,
    CalculatedFood,
    NutritionSourceCategory,
    NutrientValues,
    PortionNutrition,
)
from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS


class MealAnalysisStatus(str, Enum):
    CALCULATED = "calculated"
    FOOD_NOT_RECOGNIZED = "food_not_recognized"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"
    REQUIRES_FOOD_SELECTION = "requires_food_selection"
    REQUIRES_INGREDIENT_VERIFICATION = "requires_ingredient_verification"
    REQUIRES_RECIPE_CONFIRMATION = "requires_recipe_confirmation"


class MealAnalysisBase(BaseModel):
    recognized_foods: list[RecognizedFood]
    recognition_source: str
    analysis_session_id: int | None = None
    analysis_session_expires_at: datetime | None = None
    measured_weight_grams: Decimal | None = None
    components: list["MealAnalysisComponentResponse"] | None = None


class CalculatedMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.CALCULATED]
    food: CalculatedFood | None = None
    weight_grams: Decimal
    nutrition: PortionNutrition
    weight_source: Literal["manual", "ai_estimate"] = "manual"


class FoodNotRecognizedMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.FOOD_NOT_RECOGNIZED]


class NutritionReferenceNotFoundMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND]


class RequiresFoodSelectionMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.REQUIRES_FOOD_SELECTION]


class RequiresIngredientVerificationMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION]


class RequiresRecipeConfirmationMealAnalysis(MealAnalysisBase):
    status: Literal[MealAnalysisStatus.REQUIRES_RECIPE_CONFIRMATION]


MealAnalysisResponse = Annotated[
    CalculatedMealAnalysis
    | FoodNotRecognizedMealAnalysis
    | NutritionReferenceNotFoundMealAnalysis
    | RequiresFoodSelectionMealAnalysis
    | RequiresIngredientVerificationMealAnalysis
    | RequiresRecipeConfirmationMealAnalysis,
    Field(discriminator="status"),
]


class MealItemCreateRequest(BaseModel):
    food_id: int = Field(gt=0)
    weight_grams: Decimal = Field(gt=0, le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS, allow_inf_nan=False)


class MealCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MealItemCreateRequest] | None = Field(default=None, min_length=1, max_length=50)
    analysis_session_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def exactly_one_creation_mode(self):
        if (self.items is None) == (self.analysis_session_id is None):
            raise ValueError("Provide either manual items or analysis_session_id.")
        return self


class MealAnalysisCandidateResponse(BaseModel):
    candidate_id: UUID | None = None
    name: str


class MealAnalysisComponentResponse(BaseModel):
    component_id: UUID
    recognized_name: str
    raw_estimated_proportion: Decimal
    normalized_proportion: Decimal
    estimated_weight_grams: Decimal
    weight_source: str
    resolution_status: str
    nutrition_source: str | None
    resolved_reference: str | None
    candidates: list[MealAnalysisCandidateResponse]
    nutrition: PortionNutrition | None
    composite_estimation: bool = False
    suggested_ingredients: list["SuggestedIngredientResponse"] = Field(default_factory=list)
    recipe_matches: list["PersonalRecipeMatchResponse"] = Field(default_factory=list)


class SuggestedIngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: UUID
    name: str
    suggested_proportion: Decimal
    ingredient_source: str
    included: bool
    weight_grams: Decimal | None = None
    weight_source: str
    resolution_status: str
    candidates: list[MealAnalysisCandidateResponse] = Field(default_factory=list)
    resolved_reference: str | None = None
    nutrition_source: str | None = None
    recipe_derived: bool = False


class PersonalRecipeMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recipe_id: int
    name: str
    source: Literal["personal"]


class IngredientVerificationItemRequest(BaseModel):
    ingredient_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    included: bool
    weight_grams: Decimal | None = Field(default=None, gt=0, le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS)


class IngredientVerificationRequest(BaseModel):
    ingredients: list[IngredientVerificationItemRequest] = Field(min_length=1, max_length=50)


class IngredientCandidateSelectionRequest(BaseModel):
    ingredient_id: UUID
    candidate_id: UUID


class PersonalRecipeSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipe_id: int = Field(gt=0)


class MealAnalysisSelectionRequest(BaseModel):
    component_id: UUID
    candidate_id: UUID | None = None
    candidate_name: str | None = Field(default=None, min_length=1, max_length=160, deprecated=True)

    @model_validator(mode="after")
    def one_candidate_identifier(self):
        if (self.candidate_id is None) == (self.candidate_name is None):
            raise ValueError("Provide exactly one candidate identifier.")
        return self


class MealItemResponse(BaseModel):
    id: int
    food: CalculatedFood
    weight_grams: Decimal
    nutrition: PortionNutrition
    nutrition_source: "MealItemNutritionSource | None" = None
    composite_estimation: bool = False


class MealItemNutritionSource(BaseModel):
    """Immutable provenance snapshot for a saved meal item."""

    category: NutritionSourceCategory | None
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
