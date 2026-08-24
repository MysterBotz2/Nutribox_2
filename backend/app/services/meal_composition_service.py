from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS


WEIGHT_QUANTUM = Decimal("0.001")


@dataclass(frozen=True)
class ComposedPortion:
    normalized_proportion: Decimal
    estimated_weight_grams: Decimal


def allocate_component_weights(
    measured_weight_grams: Decimal, raw_proportions: list[Decimal]
) -> list[ComposedPortion]:
    """Normalize AI shares and reconcile weights by stable largest remainder."""
    if not measured_weight_grams.is_finite() or not Decimal("0") <= measured_weight_grams <= MAXIMUM_PROTOTYPE_WEIGHT_GRAMS:
        raise ValueError("Measured meal weight is outside the supported range.")
    if measured_weight_grams != measured_weight_grams.quantize(WEIGHT_QUANTUM):
        raise ValueError("Measured meal weight must use no more than three decimal places.")
    if not raw_proportions or any(not value.is_finite() or value < 0 for value in raw_proportions):
        raise ValueError("Component proportions must be finite non-negative values.")
    total = sum(raw_proportions, Decimal("0"))
    if total <= 0:
        raise ValueError("Component proportions must have a positive total.")
    normalized = [value / total for value in raw_proportions]
    unrounded = [measured_weight_grams * value for value in normalized]
    rounded_down = [value.quantize(WEIGHT_QUANTUM, rounding=ROUND_DOWN) for value in unrounded]
    remainder_units = int(((measured_weight_grams - sum(rounded_down, Decimal("0"))) / WEIGHT_QUANTUM).to_integral_value())
    order = sorted(range(len(unrounded)), key=lambda index: (-(unrounded[index] - rounded_down[index]), index))
    for index in order[:remainder_units]:
        rounded_down[index] += WEIGHT_QUANTUM
    return [ComposedPortion(normalized[index], rounded_down[index]) for index in range(len(normalized))]
