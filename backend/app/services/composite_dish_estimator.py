"""Provider-neutral estimation of a prepared dish's internal composition."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CompositeIngredientEstimate:
    name: str
    estimated_proportion: Decimal


@dataclass(frozen=True, slots=True)
class CompositeDishEstimate:
    dish_name: str
    ingredients: tuple[CompositeIngredientEstimate, ...]

    def __post_init__(self) -> None:
        if not self.dish_name.strip() or not self.ingredients or len(self.ingredients) > 20:
            raise ValueError("A composite estimate must contain between one and twenty ingredients.")
        if any(not ingredient.name.strip() or not ingredient.estimated_proportion.is_finite() or ingredient.estimated_proportion < 0 for ingredient in self.ingredients):
            raise ValueError("Composite ingredient names and proportions must be valid.")
        if sum((ingredient.estimated_proportion for ingredient in self.ingredients), Decimal("0")) <= 0:
            raise ValueError("Composite ingredient proportions must have a positive total.")


class CompositeDishEstimatorError(RuntimeError):
    """Safe provider-neutral failure information for dish composition estimation."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class CompositeDishEstimator(ABC):
    """Capability boundary for vendor-specific prepared-dish decomposition."""

    @abstractmethod
    def estimate_composition(
        self, *, dish_name: str, dish_weight_grams: Decimal
    ) -> CompositeDishEstimate:
        """Return ingredient groups and relative proportions only, never nutrients."""
