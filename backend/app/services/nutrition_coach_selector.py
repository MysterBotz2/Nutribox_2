from fastapi import HTTPException, status

from app.core.config import settings
from app.services.mock_nutrition_coach_provider import MockNutritionCoachProvider
from app.services.gemini_nutrition_coach_provider import GeminiNutritionCoachProvider
from app.services.nutrition_coach_provider import NutritionCoachProvider

_mock_nutrition_coach_provider = MockNutritionCoachProvider()


def get_nutrition_coach_provider() -> NutritionCoachProvider:
    """Select the configured provider without silently changing capability behavior."""
    if settings.nutrition_coach_provider == "mock":
        return _mock_nutrition_coach_provider
    if settings.nutrition_coach_provider == "gemini":
        if not settings.nutrition_coach_gemini_api_key or not settings.nutrition_coach_gemini_model:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Nutrition coach provider is not configured.")
        return GeminiNutritionCoachProvider(api_key=settings.nutrition_coach_gemini_api_key, model=settings.nutrition_coach_gemini_model, timeout_seconds=settings.nutrition_coach_gemini_timeout_seconds)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Nutrition coach provider is not configured.",
    )
