from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FoodRecognitionResult:
    """Provider-neutral food-recognition result for application services."""

    food_names: tuple[str, ...]
    source: str


class FoodRecognitionProvider(ABC):
    """Capability boundary for vendor-specific food-recognition adapters."""

    @abstractmethod
    def recognize_food(
        self, *, image_bytes: bytes, content_type: str
    ) -> FoodRecognitionResult:
        """Translate a provider response into a Nutri-Box recognition result."""
