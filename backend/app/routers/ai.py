from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.meal_repository import MealRepository
from app.repositories.nutrition_profile_repository import NutritionProfileRepository
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.schemas.ai import FoodRecognitionResponse, RecognizedFood
from app.schemas.nutrition_coach import NutritionCoachRequest, NutritionCoachResponse
from app.services.food_recognition_selector import get_food_recognition_provider
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.image_validation import read_validated_image
from app.services.nutrition_coach_provider import NutritionCoachProvider
from app.services.nutrition_coach_selector import get_nutrition_coach_provider
from app.services.nutrition_coach_service import NutritionCoachService
from app.services.nutrition_target_comparison_service import NutritionTargetComparisonService
from app.services.nutrition_target_service import NutritionTargetService
from app.services.progress_service import InvalidTimezoneError, ProgressService

router = APIRouter(prefix="/api/ai", tags=["AI capabilities"])

@router.post("/recognize-food", response_model=FoodRecognitionResponse)
async def recognize_food(
    file: UploadFile = File(description="JPEG, PNG, or WEBP food image."),
    provider: FoodRecognitionProvider = Depends(get_food_recognition_provider),
) -> FoodRecognitionResponse:
    """Return a simulated, provider-neutral food-recognition result."""
    image_bytes, content_type = await read_validated_image(file)
    result = provider.recognize_food(
        image_bytes=image_bytes,
        content_type=content_type,
    )
    return FoodRecognitionResponse(
        foods=[RecognizedFood(name=name) for name in result.food_names],
        source=result.source,
    )


def get_nutrition_coach_service(
    database_session: Annotated[Session, Depends(get_db)],
    provider: Annotated[NutritionCoachProvider, Depends(get_nutrition_coach_provider)],
) -> NutritionCoachService:
    target_repository = NutritionTargetRepository(database_session)
    progress_service = ProgressService(MealRepository(database_session))
    return NutritionCoachService(
        provider=provider,
        profile_repository=NutritionProfileRepository(database_session),
        target_service=NutritionTargetService(target_repository),
        progress_service=progress_service,
        target_comparison_service=NutritionTargetComparisonService(
            progress_service, target_repository
        ),
    )


@router.post("/coach", response_model=NutritionCoachResponse)
async def generate_nutrition_coach_guidance(
    request: NutritionCoachRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    coach_service: Annotated[NutritionCoachService, Depends(get_nutrition_coach_service)],
    timezone: str = Query("UTC", min_length=1, max_length=64),
) -> NutritionCoachResponse:
    """Return transient provider-neutral coaching guidance from trusted backend context."""
    try:
        return await coach_service.generate_guidance(current_user.id, timezone, request.question)
    except InvalidTimezoneError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
