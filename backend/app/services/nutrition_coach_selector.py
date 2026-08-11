from fastapi import HTTPException, status

from app.core.config import settings
from app.services.mock_nutrition_coach_provider import MockNutritionCoachProvider
from app.services.nutrition_coach_provider import NutritionCoachProvider

_mock_nutrition_coach_provider = MockNutritionCoachProvider()


def get_nutrition_coach_provider() -> NutritionCoachProvider:
    """Select the configured provider without silently changing capability behavior."""
    if settings.nutrition_coach_provider == "mock":
        return _mock_nutrition_coach_provider
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Nutrition coach provider is not configured.",
    )
