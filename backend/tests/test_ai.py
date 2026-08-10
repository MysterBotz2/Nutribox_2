from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, features

from app.main import app
from app.routers.ai import get_food_recognition_provider
from app.services.mock_food_recognition_provider import MockFoodRecognitionProvider

client = TestClient(app)


def create_image_bytes(image_format: str) -> bytes:
    image_bytes = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(image_bytes, format=image_format)
    return image_bytes.getvalue()


def upload_image(image_format: str, content_type: str):
    return client.post(
        "/api/ai/recognize-food",
        files={"file": (f"meal.{image_format.lower()}", create_image_bytes(image_format), content_type)},
    )


def test_recognize_food_accepts_valid_jpeg() -> None:
    response = upload_image("JPEG", "image/jpeg")

    assert response.status_code == 200
    assert response.json() == {
        "foods": [{"name": "chicken adobo"}],
        "source": "simulated",
    }


def test_recognize_food_accepts_valid_png() -> None:
    response = upload_image("PNG", "image/png")

    assert response.status_code == 200
    assert response.json()["source"] == "simulated"


@pytest.mark.skipif(not features.check("webp"), reason="Pillow has no WEBP support")
def test_recognize_food_accepts_valid_webp() -> None:
    response = upload_image("WEBP", "image/webp")

    assert response.status_code == 200
    assert response.json()["source"] == "simulated"


def test_recognize_food_rejects_unsupported_content_type() -> None:
    response = client.post(
        "/api/ai/recognize-food",
        files={"file": ("meal.gif", b"not-an-image", "image/gif")},
    )

    assert response.status_code == 415


def test_recognize_food_rejects_corrupt_image() -> None:
    response = client.post(
        "/api/ai/recognize-food",
        files={"file": ("meal.jpg", b"not-a-jpeg", "image/jpeg")},
    )

    assert response.status_code == 422


def test_recognize_food_rejects_empty_image() -> None:
    response = client.post(
        "/api/ai/recognize-food",
        files={"file": ("meal.png", b"", "image/png")},
    )

    assert response.status_code == 422


def test_recognize_food_rejects_oversized_image(monkeypatch) -> None:
    from app.routers import ai

    monkeypatch.setattr(ai.settings, "food_recognition_max_upload_bytes", 10)
    response = client.post(
        "/api/ai/recognize-food",
        files={"file": ("meal.jpg", create_image_bytes("JPEG"), "image/jpeg")},
    )

    assert response.status_code == 413


def test_recognize_food_can_use_a_different_mock_result() -> None:
    app.dependency_overrides[get_food_recognition_provider] = lambda: MockFoodRecognitionProvider(
        food_names=("steamed rice", "fried egg")
    )
    try:
        response = upload_image("PNG", "image/png")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "foods": [{"name": "steamed rice"}, {"name": "fried egg"}],
        "source": "simulated",
    }
