from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.schemas.ai import FoodRecognitionResponse, RecognizedFood
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.mock_food_recognition_provider import MockFoodRecognitionProvider

router = APIRouter(prefix="/api/ai", tags=["food recognition"])

SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
CONTENT_TYPE_BY_IMAGE_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

_mock_food_recognition_provider = MockFoodRecognitionProvider()


def get_food_recognition_provider() -> FoodRecognitionProvider:
    """Select the configured food-recognition provider implementation."""
    if settings.food_recognition_provider == "mock":
        return _mock_food_recognition_provider

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Food recognition provider is not configured.",
    )


async def _read_validated_image(file: UploadFile) -> tuple[bytes, str]:
    content_type = (file.content_type or "").split(";", maxsplit=1)[0].lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, and WEBP images are supported.",
        )

    image_bytes = await file.read(settings.food_recognition_max_upload_bytes + 1)
    await file.close()

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image upload is empty.",
        )
    if len(image_bytes) > settings.food_recognition_max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image upload exceeds the configured size limit.",
        )

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image_format = image.format
            image.verify()
    except (Image.DecompressionBombError, OSError, UnidentifiedImageError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image upload is invalid or corrupted.",
        ) from None

    if CONTENT_TYPE_BY_IMAGE_FORMAT.get(image_format) != content_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image content does not match its declared MIME type.",
        )

    return image_bytes, content_type


@router.post("/recognize-food", response_model=FoodRecognitionResponse)
async def recognize_food(
    file: UploadFile = File(description="JPEG, PNG, or WEBP food image."),
    provider: FoodRecognitionProvider = Depends(get_food_recognition_provider),
) -> FoodRecognitionResponse:
    """Return a simulated, provider-neutral food-recognition result."""
    image_bytes, content_type = await _read_validated_image(file)
    result = provider.recognize_food(
        image_bytes=image_bytes,
        content_type=content_type,
    )
    return FoodRecognitionResponse(
        foods=[RecognizedFood(name=name) for name in result.food_names],
        source=result.source,
    )
