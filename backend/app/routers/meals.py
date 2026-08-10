from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.routers.nutrition import get_nutrition_service
from app.schemas.meal import MealAnalysisResponse
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.food_recognition_selector import get_food_recognition_provider
from app.services.image_validation import read_validated_image
from app.services.meal_analysis_service import MealAnalysisService
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/api/meals", tags=["meal analysis"])


def get_meal_analysis_service(
    provider: Annotated[FoodRecognitionProvider, Depends(get_food_recognition_provider)],
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
) -> MealAnalysisService:
    """Provide the vendor-neutral transient meal analysis orchestration service."""
    return MealAnalysisService(provider, nutrition_service)


@router.post("/analyze", response_model=MealAnalysisResponse)
async def analyze_meal(
    file: UploadFile = File(description="JPEG, PNG, or WEBP meal image."),
    weight_grams: Decimal = Form(
        ge=0,
        le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS,
        allow_inf_nan=False,
        description="Manual portion weight in grams, from 0 to 5000.",
    ),
    meal_analysis_service: MealAnalysisService = Depends(get_meal_analysis_service),
) -> MealAnalysisResponse:
    """Analyze a transient meal image and full portion weight without saving a meal."""
    image_bytes, content_type = await read_validated_image(file)
    return meal_analysis_service.analyze(
        image_bytes=image_bytes,
        content_type=content_type,
        weight_grams=weight_grams,
    )
