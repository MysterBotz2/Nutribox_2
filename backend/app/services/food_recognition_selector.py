from fastapi import HTTPException, status

from app.core.config import settings
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.mock_food_recognition_provider import MockFoodRecognitionProvider

_mock_food_recognition_provider = MockFoodRecognitionProvider()


def get_food_recognition_provider() -> FoodRecognitionProvider:
    """Select the configured food-recognition provider implementation."""
    if settings.food_recognition_provider == "mock":
        return _mock_food_recognition_provider
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Food recognition provider is not configured.",
    )
