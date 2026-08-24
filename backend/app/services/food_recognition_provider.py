from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class RecognizedMealComponent:
    """One separately served, visible food or composite dish."""

    name: str
    estimated_proportion: Decimal


@dataclass(frozen=True, slots=True)
class FoodRecognitionResult:
    """Provider-neutral food-recognition result for application services."""

    source: str
    components: tuple[RecognizedMealComponent, ...] = ()
    food_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Accept legacy name-only providers while making components canonical."""
        if self.components and self.food_names:
            if self.food_names != tuple(component.name for component in self.components):
                raise ValueError("Recognition names and components disagree.")
        elif self.food_names:
            object.__setattr__(
                self,
                "components",
                tuple(RecognizedMealComponent(name=name, estimated_proportion=Decimal("1")) for name in self.food_names),
            )
        else:
            object.__setattr__(self, "food_names", tuple(component.name for component in self.components))


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
