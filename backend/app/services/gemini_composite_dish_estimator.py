"""Gemini adapter for composition-only prepared-dish estimation."""

from decimal import Decimal
import logging
from typing import Any

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.composite_dish_estimator import (
    CompositeDishEstimate,
    CompositeDishEstimator,
    CompositeDishEstimatorError,
    CompositeIngredientEstimate,
)


_COMPOSITION_INSTRUCTION = (
    "Estimate the internal edible composition of one recognized prepared dish for portion allocation. "
    "Return plausible, resolvable ingredient groups and relative proportions only; proportions need not sum to one. "
    "Do not provide calories, macros, micronutrients, nutrition values, recipe instructions, confidence, or explanation. "
    "Do not claim exact recipe knowledge. Avoid excessive trace garnish or seasoning groups unless materially edible."
)

logger = logging.getLogger(__name__)


_COMPOSITION_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "ingredients": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "estimated_proportion": types.Schema(type=types.Type.NUMBER),
                },
                required=["name", "estimated_proportion"],
            ),
        ),
    },
    required=["ingredients"],
)


class _GeminiIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    estimated_proportion: Decimal


class _GeminiCompositionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredients: list[_GeminiIngredient] = Field(min_length=1, max_length=20)


class GeminiCompositeDishEstimator(CompositeDishEstimator):
    def __init__(self, *, api_key: str, model: str, timeout_seconds: int, client: Any | None = None) -> None:
        if not api_key.strip() or not model.strip():
            raise ValueError("Gemini API key and model must be configured.")
        self._model = model
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,
                retry_options=types.HttpRetryOptions(attempts=2, initial_delay=0.25, max_delay=1.0, http_status_codes=[429, 503]),
            ),
        )

    def estimate_composition(self, *, dish_name: str, dish_weight_grams: Decimal) -> CompositeDishEstimate:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[_COMPOSITION_INSTRUCTION, f"Dish: {dish_name}\nPortion weight: {dish_weight_grams} g"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_COMPOSITION_RESPONSE_SCHEMA,
                ),
            )
        except errors.APIError as exception:
            logger.warning(
                "composite_dish_estimation outcome=provider_request_failure model=%s "
                "exception_class=%s provider_status_code=%s provider_status=%s",
                self._model,
                type(exception).__name__,
                exception.code,
                exception.status,
            )
            raise self._translate_api_error(exception) from None
        except httpx.TimeoutException:
            logger.warning(
                "composite_dish_estimation outcome=provider_timeout model=%s exception_class=%s",
                self._model,
                "TimeoutException",
            )
            raise CompositeDishEstimatorError("Composite dish estimation provider timed out.", 504) from None
        except httpx.RequestError:
            logger.warning(
                "composite_dish_estimation outcome=provider_unavailable model=%s exception_class=%s",
                self._model,
                "RequestError",
            )
            raise CompositeDishEstimatorError("Composite dish estimation provider is unavailable.", 503) from None
        except Exception as exception:
            logger.error(
                "composite_dish_estimation outcome=provider_unexpected_error model=%s exception_class=%s",
                self._model,
                type(exception).__name__,
            )
            raise CompositeDishEstimatorError("Composite dish estimation provider returned an unexpected error.", 502) from None
        try:
            parsed = _GeminiCompositionPayload.model_validate(response.parsed)
            estimate = CompositeDishEstimate(
                dish_name=dish_name,
                ingredients=tuple(
                    CompositeIngredientEstimate(" ".join(item.name.split()), item.estimated_proportion)
                    for item in parsed.ingredients
                ),
            )
        except (AttributeError, TypeError, ValidationError, ValueError) as exception:
            logger.warning(
                "composite_dish_estimation outcome=invalid_provider_output model=%s "
                "exception_class=%s response_parsing_failed=%s schema_validation_failed=%s "
                "validation_category=%s",
                self._model,
                type(exception).__name__,
                isinstance(exception, (AttributeError, TypeError)),
                isinstance(exception, ValidationError),
                self._validation_category(exception),
            )
            raise CompositeDishEstimatorError("Composite dish estimation provider returned an invalid response.", 502) from None
        logger.info(
            "composite_dish_estimation outcome=success model=%s ingredient_count=%d",
            self._model,
            len(estimate.ingredients),
        )
        return estimate

    @staticmethod
    def _validation_category(exception: Exception) -> str:
        if isinstance(exception, AttributeError):
            return "missing_response_parsed"
        if isinstance(exception, TypeError):
            return "unexpected_response_type"
        if isinstance(exception, ValidationError):
            errors = exception.errors()
            if any(error["type"] == "missing" for error in errors):
                return "missing_required_field"
            if any(error["type"] == "extra_forbidden" for error in errors):
                return "extra_field"
            if any("decimal" in error["type"] for error in errors):
                return "invalid_proportion_type"
            return "schema_validation_failed"
        return "invalid_composition"

    @staticmethod
    def _translate_api_error(exception: errors.APIError) -> CompositeDishEstimatorError:
        if exception.code in {401, 403, 500, 502, 503}:
            return CompositeDishEstimatorError("Composite dish estimation provider is unavailable.", 503)
        if exception.code == 429:
            return CompositeDishEstimatorError("Composite dish estimation provider rate limit was reached.", 429)
        if exception.code in {408, 504}:
            return CompositeDishEstimatorError("Composite dish estimation provider timed out.", 504)
        return CompositeDishEstimatorError("Composite dish estimation provider request failed.", 502)
