from app.services.food_recognition_provider import (
    FoodRecognitionProvider,
    FoodRecognitionResult,
    RecognizedMealComponent,
)
from decimal import Decimal


class MockFoodRecognitionProvider(FoodRecognitionProvider):
    """Development-only provider that returns deterministic simulated food names."""

    def __init__(
        self,
        food_names: tuple[str, ...] = ("chicken adobo",),
        components: tuple[RecognizedMealComponent, ...] | None = None,
    ) -> None:
        self._components = components or tuple(
            RecognizedMealComponent(name=name, estimated_proportion=Decimal("1"))
            for name in food_names
        )

    def recognize_food(
        self, *, image_bytes: bytes, content_type: str
    ) -> FoodRecognitionResult:
        return FoodRecognitionResult(
            components=self._components,
            source="simulated",
        )
