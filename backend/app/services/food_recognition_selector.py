from fastapi import HTTPException, status

from app.core.config import settings
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.gemini_food_recognition_provider import GeminiFoodRecognitionProvider
from app.services.mock_food_recognition_provider import MockFoodRecognitionProvider

_mock_food_recognition_provider = MockFoodRecognitionProvider()


def get_food_recognition_provider() -> FoodRecognitionProvider:
    """Select the configured food-recognition provider implementation."""
    if settings.food_recognition_provider == "mock":
        return _mock_food_recognition_provider
    if settings.food_recognition_provider == "gemini":
        if not settings.gemini_api_key or not settings.gemini_model:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini food recognition provider is not configured.",
            )
        return GeminiFoodRecognitionProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.gemini_timeout_seconds,
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Food recognition provider is not configured.",
    )
