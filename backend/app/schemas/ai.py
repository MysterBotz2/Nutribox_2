from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAXIMUM_RECOGNIZED_FOODS = 10


class RecognizedFood(BaseModel):
    """A normalized food identity returned by any recognition provider."""

    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Food name must not be blank.")
        return normalized_value


class FoodRecognitionResponse(BaseModel):
    """Provider-neutral response for a food-recognition request."""

    foods: list[RecognizedFood] = Field(max_length=MAXIMUM_RECOGNIZED_FOODS)
    source: Literal["simulated", "gemini"]
