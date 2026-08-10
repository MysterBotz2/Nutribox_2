from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import settings
from app.schemas.ai import FoodRecognitionResponse, RecognizedFood
from app.services.food_recognition_selector import get_food_recognition_provider
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.image_validation import read_validated_image

router = APIRouter(prefix="/api/ai", tags=["food recognition"])

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
