from dataclasses import dataclass
from io import BytesIO

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from google.genai import errors
from PIL import Image

from app.main import app
from app.routers.ai import get_food_recognition_provider
from app.services.food_recognition_provider import FoodRecognitionProviderError
from app.services.food_recognition_provider import FoodRecognitionResult
from app.services.food_recognition_selector import get_food_recognition_provider as select_provider
from app.services.gemini_food_recognition_provider import GeminiFoodRecognitionProvider


@dataclass
class FakeResponse:
    parsed: object


class FakeModels:
    def __init__(self, response: object | Exception) -> None:
        self.response = response
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeClient:
    def __init__(self, response: object | Exception) -> None:
        self.models = FakeModels(response)


def make_provider(response: object | Exception) -> tuple[GeminiFoodRecognitionProvider, FakeClient]:
    client = FakeClient(response)
    return (
        GeminiFoodRecognitionProvider(
            api_key="test-key-not-for-network", model="test-model", timeout_seconds=9, client=client
        ),
        client,
    )


def test_gemini_maps_single_food_and_passes_only_image_bytes_and_mime_type() -> None:
    provider, client = make_provider(FakeResponse({"food_names": [" Chicken   Adobo "]}))

    result = provider.recognize_food(image_bytes=b"image-bytes", content_type="image/jpeg")

    assert result.food_names == ("Chicken Adobo",)
    assert result.source == "gemini"
    call = client.models.calls[0]
    assert call["model"] == "test-model"
    assert call["contents"][1].inline_data.data == b"image-bytes"
    assert call["contents"][1].inline_data.mime_type == "image/jpeg"
    assert "confidence" not in str(call["config"].model_dump()).casefold()


def test_gemini_maps_multiple_foods_and_non_food_result() -> None:
    provider, _ = make_provider(FakeResponse({"food_names": ["rice", "fried egg"]}))
    assert provider.recognize_food(image_bytes=b"x", content_type="image/png").food_names == ("rice", "fried egg")

    provider, _ = make_provider(FakeResponse({"food_names": []}))
    assert provider.recognize_food(image_bytes=b"x", content_type="image/png").food_names == ()


@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_detail"),
    [
        (errors.APIError(401, {}), 503, "authentication failed"),
        (errors.APIError(429, {}), 429, "rate limit"),
        (httpx.TimeoutException("timeout"), 504, "timed out"),
    ],
)
def test_gemini_provider_errors_are_translated_safely(exception, expected_status, expected_detail) -> None:
    provider, _ = make_provider(exception)

    with pytest.raises(FoodRecognitionProviderError) as raised:
        provider.recognize_food(image_bytes=b"x", content_type="image/webp")

    assert raised.value.status_code == expected_status
    assert expected_detail in raised.value.detail
    assert "test-key-not-for-network" not in raised.value.detail


def test_gemini_invalid_structured_output_is_safe() -> None:
    provider, _ = make_provider(FakeResponse({"food_names": [""]}))
    with pytest.raises(FoodRecognitionProviderError, match="invalid response"):
        provider.recognize_food(image_bytes=b"x", content_type="image/jpeg")


def test_selector_uses_gemini_and_validates_its_configuration(monkeypatch) -> None:
    from app.services import food_recognition_selector as selector

    monkeypatch.setattr(selector.settings, "food_recognition_provider", "gemini")
    monkeypatch.setattr(selector.settings, "gemini_api_key", "configured-key")
    monkeypatch.setattr(selector.settings, "gemini_model", "configured-model")
    assert isinstance(select_provider(), GeminiFoodRecognitionProvider)

    monkeypatch.setattr(selector.settings, "gemini_api_key", None)
    with pytest.raises(HTTPException) as missing_key:
        select_provider()
    assert missing_key.value.status_code == 503

    monkeypatch.setattr(selector.settings, "gemini_api_key", "configured-key")
    monkeypatch.setattr(selector.settings, "gemini_model", None)
    with pytest.raises(HTTPException) as missing_model:
        select_provider()
    assert missing_model.value.status_code == 503


def test_missing_gemini_configuration_does_not_affect_mock(monkeypatch) -> None:
    from app.services import food_recognition_selector as selector
    from app.services.mock_food_recognition_provider import MockFoodRecognitionProvider

    monkeypatch.setattr(selector.settings, "food_recognition_provider", "mock")
    monkeypatch.setattr(selector.settings, "gemini_api_key", None)
    monkeypatch.setattr(selector.settings, "gemini_model", None)
    assert isinstance(select_provider(), MockFoodRecognitionProvider)


def test_endpoint_returns_safe_provider_error_without_vendor_details() -> None:
    class FailingProvider:
        def recognize_food(self, *, image_bytes: bytes, content_type: str):
            raise FoodRecognitionProviderError("Food recognition provider timed out.", 504)

    app.dependency_overrides[get_food_recognition_provider] = lambda: FailingProvider()
    try:
        image = BytesIO()
        Image.new("RGB", (4, 4), color="white").save(image, format="PNG")
        response = TestClient(app).post(
            "/api/ai/recognize-food",
            files={"file": ("meal.png", image.getvalue(), "image/png")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 504
    assert response.json() == {"detail": "Food recognition provider timed out."}


def test_endpoint_accepts_gemini_source_and_empty_non_food_result() -> None:
    class NonFoodGeminiProvider:
        def recognize_food(self, *, image_bytes: bytes, content_type: str):
            return FoodRecognitionResult(food_names=(), source="gemini")

    app.dependency_overrides[get_food_recognition_provider] = lambda: NonFoodGeminiProvider()
    try:
        image = BytesIO()
        Image.new("RGB", (4, 4), color="white").save(image, format="PNG")
        response = TestClient(app).post(
            "/api/ai/recognize-food",
            files={"file": ("meal.png", image.getvalue(), "image/png")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"foods": [], "source": "gemini"}
