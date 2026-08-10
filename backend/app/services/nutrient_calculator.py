from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.schemas.nutrition import NutritionPer100g, PortionNutrition

REFERENCE_WEIGHT_GRAMS = Decimal("100")
PORTION_NUTRIENT_QUANTUM = Decimal("0.001")


class NutrientCalculator:
    """Pure Decimal-based conversion from per-100-gram values to a portion."""

    def calculate(
        self, nutrition_per_100g: NutritionPer100g, weight_grams: Decimal
    ) -> PortionNutrition:
        """Calculate and centrally round all nutrients for one portion weight."""
        validated_weight = self._validate_weight(weight_grams)
        multiplier = validated_weight / REFERENCE_WEIGHT_GRAMS

        return PortionNutrition(
            calories=self._round(nutrition_per_100g.calories * multiplier),
            protein_g=self._round(nutrition_per_100g.protein_g * multiplier),
            carbohydrates_g=self._round(
                nutrition_per_100g.carbohydrates_g * multiplier
            ),
            fat_g=self._round(nutrition_per_100g.fat_g * multiplier),
            fiber_g=self._round(nutrition_per_100g.fiber_g * multiplier),
        )

    @staticmethod
    def _validate_weight(weight_grams: Decimal) -> Decimal:
        try:
            decimal_weight = (
                weight_grams
                if isinstance(weight_grams, Decimal)
                else Decimal(str(weight_grams))
            )
        except (InvalidOperation, ValueError) as error:
            raise ValueError("Weight must be a valid decimal value.") from error

        if not decimal_weight.is_finite():
            raise ValueError("Weight must be finite.")
        if decimal_weight < 0:
            raise ValueError("Weight must be greater than or equal to zero.")
        if decimal_weight > MAXIMUM_PROTOTYPE_WEIGHT_GRAMS:
            raise ValueError("Weight exceeds the prototype maximum of 5000 grams.")
        return decimal_weight

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        return value.quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP)
