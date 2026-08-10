from app.services.food_recognition_provider import (
    FoodRecognitionProvider,
    FoodRecognitionResult,
)


class MockFoodRecognitionProvider(FoodRecognitionProvider):
    """Development-only provider that returns deterministic simulated food names."""

    def __init__(self, food_names: tuple[str, ...] = ("chicken adobo",)) -> None:
        self._food_names = food_names

    def recognize_food(
        self, *, image_bytes: bytes, content_type: str
    ) -> FoodRecognitionResult:
        return FoodRecognitionResult(
            food_names=self._food_names,
            source="simulated",
        )
