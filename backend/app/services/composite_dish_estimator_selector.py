from fastapi import HTTPException, status

from app.core.config import settings
from app.services.composite_dish_estimator import CompositeDishEstimator
from app.services.gemini_composite_dish_estimator import GeminiCompositeDishEstimator
from app.services.mock_composite_dish_estimator import MockCompositeDishEstimator


_mock_estimator = MockCompositeDishEstimator()


def get_composite_dish_estimator() -> CompositeDishEstimator:
    """Use the food-recognition provider setting without adding another secret."""
    if settings.food_recognition_provider == "mock":
        return _mock_estimator
    if settings.food_recognition_provider == "gemini":
        if not settings.gemini_api_key or not settings.gemini_model:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Gemini composite dish estimator is not configured.")
        return GeminiCompositeDishEstimator(api_key=settings.gemini_api_key, model=settings.gemini_model, timeout_seconds=settings.gemini_timeout_seconds)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Composite dish estimator is not configured.")
