"""Gemini adapter for Nutri-Box's provider-neutral food-recognition capability."""

from __future__ import annotations

from typing import Any

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError

from app.services.food_recognition_provider import (
    FoodRecognitionProvider,
    FoodRecognitionProviderError,
    FoodRecognitionResult,
)


_RECOGNITION_INSTRUCTION = (
    "Identify only visible edible food items in this image. Use cautious, common and "
    "reasonably specific food or dish names. Separate distinct visible foods. Do not "
    "invent hidden ingredients. Do not provide nutrition calculations, portion weights, "
    "dietary recommendations, confidence scores, or any explanation. If no identifiable "
    "food is visible, return an empty list."
)


class _GeminiRecognitionPayload(BaseModel):
    food_names: list[str] = Field(default_factory=list)


class GeminiFoodRecognitionProvider(FoodRecognitionProvider):
    """Translate Gemini structured image output into Nutri-Box food labels only."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
        client: Any | None = None,
    ) -> None:
        if not api_key.strip() or not model.strip():
            raise ValueError("Gemini API key and model must be configured.")
        self._model = model
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(
                    attempts=2,
                    initial_delay=0.25,
                    max_delay=1.0,
                    http_status_codes=[429, 503],
                ),
            ),
        )

    def recognize_food(
        self, *, image_bytes: bytes, content_type: str
    ) -> FoodRecognitionResult:
        """Recognize visible food labels from already-validated in-memory image bytes."""
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[
                    _RECOGNITION_INSTRUCTION,
                    types.Part.from_bytes(data=image_bytes, mime_type=content_type),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_GeminiRecognitionPayload,
                ),
            )
            
        except errors.APIError as exception:
            raise self._translate_api_error(exception) from None
        except httpx.TimeoutException:
            raise FoodRecognitionProviderError(
                "Food recognition provider timed out.", status_code=504
            ) from None
        except httpx.RequestError:
            raise FoodRecognitionProviderError(
                "Food recognition provider is unavailable.", status_code=503
            ) from None
        except Exception:
            raise FoodRecognitionProviderError(
                "Food recognition provider returned an unexpected error.", status_code=502
            ) from None

        try:
            parsed = _GeminiRecognitionPayload.model_validate(response.parsed)
            names = tuple(self._validate_name(name) for name in parsed.food_names)
        except (AttributeError, TypeError, ValidationError, ValueError):
            raise FoodRecognitionProviderError(
                "Food recognition provider returned an invalid response.", status_code=502
            ) from None
        return FoodRecognitionResult(food_names=names, source="gemini")

    @staticmethod
    def _validate_name(value: str) -> str:
        name = " ".join(value.split())
        if not name or len(name) > 160:
            raise ValueError("Invalid recognized food name.")
        return name

    @staticmethod
    def _translate_api_error(exception: errors.APIError) -> FoodRecognitionProviderError:
        code = exception.code
        if code in {401, 403}:
            return FoodRecognitionProviderError(
                "Food recognition provider authentication failed.", status_code=503
            )
        if code == 429:
            return FoodRecognitionProviderError(
                "Food recognition provider rate limit was reached.", status_code=429
            )
        if code in {408, 504}:
            return FoodRecognitionProviderError(
                "Food recognition provider timed out.", status_code=504
            )
        if code in {500, 502, 503}:
            return FoodRecognitionProviderError(
                "Food recognition provider is unavailable.", status_code=503
            )
        return FoodRecognitionProviderError(
            "Food recognition provider request failed.", status_code=502
        )
