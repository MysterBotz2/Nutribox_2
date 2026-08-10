from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

SUPPORTED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
CONTENT_TYPE_BY_IMAGE_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


async def read_validated_image(file: UploadFile) -> tuple[bytes, str]:
    """Read one allowed image into memory after validating its actual format."""
    content_type = (file.content_type or "").split(";", maxsplit=1)[0].lower()
    if content_type not in SUPPORTED_IMAGE_CONTENT_TYPES:
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
