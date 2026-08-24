"""Gemini adapter for Nutri-Box's provider-neutral food-recognition capability."""

from __future__ import annotations

from typing import Any
from decimal import Decimal

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.services.food_recognition_provider import (
    FoodRecognitionProvider,
    FoodRecognitionProviderError,
    FoodRecognitionResult,
    RecognizedMealComponent,
)


_RECOGNITION_INSTRUCTION = (
    "Identify only visible top-level plated foods or dishes that are separately served and "
    "should receive their own nutrition reference. Use cautious, common and reasonably "
    "specific food or dish names. For a composite dish such as stew, soup, curry, sandwich, "
    "pizza, salad, or casserole, return the composite dish itself rather than also listing "
    "its internal ingredients. Return an ingredient only when it is visibly served as a "
    "distinct food item. Do not invent hidden ingredients. Do not provide nutrition "
    "calculations, calorie estimates, authoritative gram weights, dietary recommendations, "
    "confidence scores, or any explanation. Estimate each component's relative share of the "
    "visible edible meal; proportions need not sum to one because the backend normalizes them. "
    "If no identifiable food is visible, return an empty list."
)

# A small defensive guard for common parser over-expansion. The Gemini prompt is
# the primary control; this list only removes generic ingredient labels when a
# recognized composite dish is already present. It intentionally excludes common
# separately served sides such as rice.
_COMPOSITE_DISH_TERMS = frozenset({"stew", "soup", "curry", "sandwich", "pizza", "salad", "casserole"})
_GENERIC_COMPOSITE_INGREDIENTS = frozenset({
    "beef", "chicken", "pork", "meat", "bread", "carrot", "potato", "lettuce", "tomato", "onion", "cheese",
    "cucumber", "vegetables", "green bell pepper", "red bell pepper", "green olives",
})


class _GeminiRecognitionComponent(BaseModel):
    name: str
    estimated_proportion: Decimal


class _GeminiRecognitionPayload(BaseModel):
    components: list[_GeminiRecognitionComponent] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def adapt_legacy_names(cls, value: object) -> object:
        if isinstance(value, dict) and "components" not in value and "food_names" in value:
            names = value["food_names"]
            return {"components": [{"name": name, "estimated_proportion": "1"} for name in names]}
        return value


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
            components = self._normalize_top_level_foods(
                tuple(
                    RecognizedMealComponent(
                        name=self._validate_name(component.name),
                        estimated_proportion=self._validate_proportion(component.estimated_proportion),
                    )
                    for component in parsed.components
                )
            )
        except (AttributeError, TypeError, ValidationError, ValueError):
            raise FoodRecognitionProviderError(
                "Food recognition provider returned an invalid response.", status_code=502
            ) from None
        if components and sum((component.estimated_proportion for component in components), Decimal("0")) <= 0:
            raise FoodRecognitionProviderError("Food recognition provider returned an invalid response.", status_code=502)
        return FoodRecognitionResult(components=components, source="gemini")

    @staticmethod
    def _validate_name(value: str) -> str:
        name = " ".join(value.split())
        if not name or len(name) > 160:
            raise ValueError("Invalid recognized food name.")
        return name

    @staticmethod
    def _validate_proportion(value: Decimal) -> Decimal:
        if not value.is_finite() or value < 0:
            raise ValueError("Invalid recognized food proportion.")
        return value

    @staticmethod
    def _normalize_top_level_foods(
        components: tuple[RecognizedMealComponent, ...]
    ) -> tuple[RecognizedMealComponent, ...]:
        """Remove duplicate ingredient labels beneath an already-recognized dish."""
        deduplicated: list[str] = []
        seen: set[str] = set()
        for component in components:
            normalized = component.name.casefold()
            if normalized not in seen:
                seen.add(normalized)
                deduplicated.append(component)

        has_composite = any(
            set(component.name.casefold().replace("-", " ").split()) & _COMPOSITE_DISH_TERMS
            for component in deduplicated
        )
        if not has_composite:
            return tuple(deduplicated)
        return tuple(
            component for component in deduplicated
            if component.name.casefold() not in _GENERIC_COMPOSITE_INGREDIENTS
        )

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
