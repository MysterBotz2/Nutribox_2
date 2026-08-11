from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FoodRecognitionResult:
    """Provider-neutral food-recognition result for application services."""

    food_names: tuple[str, ...]
    source: str


class FoodRecognitionProviderError(RuntimeError):
    """Safe, provider-neutral failure information for food recognition."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class FoodRecognitionProvider(ABC):
    """Capability boundary for vendor-specific food-recognition adapters."""

    @abstractmethod
    def recognize_food(
        self, *, image_bytes: bytes, content_type: str
    ) -> FoodRecognitionResult:
        """Translate a provider response into a Nutri-Box recognition result."""
