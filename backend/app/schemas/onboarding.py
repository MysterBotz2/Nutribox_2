from enum import Enum

from pydantic import BaseModel, Field


class OnboardingRequiredField(str, Enum):
    SENSITIVE_CONSENT = "sensitive_consent"
    MEDICAL_CONDITIONS = "medical_conditions"
    SMOKING_HISTORY = "smoking_history"
    DRINKING_HISTORY = "drinking_history"
    BODY_BUILD = "body_build"
    ALLERGIES = "allergies"
    MEDICAL_NEEDS = "medical_needs"
    LIFESTYLE_DIETS = "lifestyle_diets"
    ACTIVITY_LEVEL = "activity_level"
    BUDGET_ALLOTMENT = "budget_allotment"
    NUTRITION_GOAL = "nutrition_goal"


class OnboardingStatusResponse(BaseModel):
    """Derived owner-only completion metadata with no profile values."""

    completed: bool
    missing_required_fields: list[OnboardingRequiredField] = Field(default_factory=list)
