from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.schemas.nutrition import NutritionPer100g, PortionNutrition

REFERENCE_WEIGHT_GRAMS = Decimal("100")
PORTION_NUTRIENT_QUANTUM = Decimal("0.001")
KILOJOULES_PER_KILOCALORIE = Decimal("4.184")


def derive_energy_kj(calories: Decimal | None) -> Decimal | None:
    """Derive kJ from calories at the presentation boundary."""
    return None if calories is None else calories_to_energy_kj(calories)


def calories_to_energy_kj(calories: Decimal) -> Decimal:
    return (calories * KILOJOULES_PER_KILOCALORIE).quantize(
        PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP
    )


@dataclass(frozen=True)
class ExtendedNutritionPer100g:
    """Internal V2 nutrition reference values expressed per 100 grams."""

    calories: Decimal
    protein_g: Decimal
    carbohydrates_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal
    saturated_fat_g: Decimal | None
    sugars_g: Decimal | None
    sodium_mg: Decimal | None
    cholesterol_mg: Decimal | None
    omega_3_g: Decimal | None
    omega_6_g: Decimal | None
    calcium_mg: Decimal | None
    potassium_mg: Decimal | None
    zinc_mg: Decimal | None
    iron_mg: Decimal | None
    magnesium_mg: Decimal | None
    vitamin_a_mcg_rae: Decimal | None
    vitamin_b12_mcg: Decimal | None
    vitamin_c_mg: Decimal | None
    vitamin_d_mcg: Decimal | None
    folate_mcg_dfe: Decimal | None
    phosphorus_mg: Decimal | None = None
    vitamin_b6_mg: Decimal | None = None
    niacin_mg: Decimal | None = None

    @classmethod
    def from_legacy(cls, nutrition: NutritionPer100g) -> "ExtendedNutritionPer100g":
        """Adapt the stable five-nutrient API representation without fabricating values."""
        return cls(
            calories=nutrition.calories,
            protein_g=nutrition.protein_g,
            carbohydrates_g=nutrition.carbohydrates_g,
            fat_g=nutrition.fat_g,
            fiber_g=nutrition.fiber_g,
            saturated_fat_g=None,
            sugars_g=None,
            sodium_mg=None,
            cholesterol_mg=None,
            omega_3_g=None,
            omega_6_g=None,
            calcium_mg=None,
            potassium_mg=None,
            zinc_mg=None,
            iron_mg=None,
            magnesium_mg=None,
            vitamin_a_mcg_rae=None,
            vitamin_b12_mcg=None,
            vitamin_c_mg=None,
            vitamin_d_mcg=None,
            folate_mcg_dfe=None,
            phosphorus_mg=None,
            vitamin_b6_mg=None,
            niacin_mg=None,
        )


@dataclass(frozen=True)
class ExtendedPortionNutrition:
    """Internal deterministic V2 portion result; optional values preserve unknowns."""

    calories: Decimal
    protein_g: Decimal
    carbohydrates_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal
    saturated_fat_g: Decimal | None
    sugars_g: Decimal | None
    sodium_mg: Decimal | None
    cholesterol_mg: Decimal | None
    omega_3_g: Decimal | None
    omega_6_g: Decimal | None
    calcium_mg: Decimal | None
    potassium_mg: Decimal | None
    zinc_mg: Decimal | None
    iron_mg: Decimal | None
    magnesium_mg: Decimal | None
    vitamin_a_mcg_rae: Decimal | None
    vitamin_b12_mcg: Decimal | None
    vitamin_c_mg: Decimal | None
    vitamin_d_mcg: Decimal | None
    folate_mcg_dfe: Decimal | None
    energy_kj: Decimal | None = None
    phosphorus_mg: Decimal | None = None
    vitamin_b6_mg: Decimal | None = None
    niacin_mg: Decimal | None = None

    def to_legacy_portion_nutrition(self) -> PortionNutrition:
        """Project the stable public five-nutrient response without changing its contract."""
        return PortionNutrition(
            calories=self.calories,
            protein_g=self.protein_g,
            carbohydrates_g=self.carbohydrates_g,
            fat_g=self.fat_g,
            fiber_g=self.fiber_g,
        )


class NutrientCalculator:
    """Pure Decimal-based conversion from per-100-gram values to a portion."""

    def calculate(
        self, nutrition_per_100g: NutritionPer100g, weight_grams: Decimal
    ) -> PortionNutrition:
        """Calculate the stable five-nutrient public portion representation."""
        return self.calculate_extended(
            ExtendedNutritionPer100g.from_legacy(nutrition_per_100g), weight_grams
        ).to_legacy_portion_nutrition()

    def calculate_extended(
        self, nutrition_per_100g: ExtendedNutritionPer100g, weight_grams: Decimal
    ) -> ExtendedPortionNutrition:
        """Calculate all known V2 nutrients and preserve unknown values as ``None``."""
        validated_weight = self._validate_weight(weight_grams)
        multiplier = validated_weight / REFERENCE_WEIGHT_GRAMS

        return ExtendedPortionNutrition(
            calories=self._round(nutrition_per_100g.calories * multiplier),
            protein_g=self._round(nutrition_per_100g.protein_g * multiplier),
            carbohydrates_g=self._round(
                nutrition_per_100g.carbohydrates_g * multiplier
            ),
            fat_g=self._round(nutrition_per_100g.fat_g * multiplier),
            fiber_g=self._round(nutrition_per_100g.fiber_g * multiplier),
            saturated_fat_g=self._scale_optional(
                nutrition_per_100g.saturated_fat_g, multiplier
            ),
            sugars_g=self._scale_optional(nutrition_per_100g.sugars_g, multiplier),
            sodium_mg=self._scale_optional(nutrition_per_100g.sodium_mg, multiplier),
            cholesterol_mg=self._scale_optional(
                nutrition_per_100g.cholesterol_mg, multiplier
            ),
            omega_3_g=self._scale_optional(nutrition_per_100g.omega_3_g, multiplier),
            omega_6_g=self._scale_optional(nutrition_per_100g.omega_6_g, multiplier),
            calcium_mg=self._scale_optional(nutrition_per_100g.calcium_mg, multiplier),
            potassium_mg=self._scale_optional(nutrition_per_100g.potassium_mg, multiplier),
            zinc_mg=self._scale_optional(nutrition_per_100g.zinc_mg, multiplier),
            iron_mg=self._scale_optional(nutrition_per_100g.iron_mg, multiplier),
            magnesium_mg=self._scale_optional(nutrition_per_100g.magnesium_mg, multiplier),
            phosphorus_mg=self._scale_optional(nutrition_per_100g.phosphorus_mg, multiplier),
            vitamin_b6_mg=self._scale_optional(nutrition_per_100g.vitamin_b6_mg, multiplier),
            niacin_mg=self._scale_optional(nutrition_per_100g.niacin_mg, multiplier),
            vitamin_a_mcg_rae=self._scale_optional(
                nutrition_per_100g.vitamin_a_mcg_rae, multiplier
            ),
            vitamin_b12_mcg=self._scale_optional(
                nutrition_per_100g.vitamin_b12_mcg, multiplier
            ),
            vitamin_c_mg=self._scale_optional(nutrition_per_100g.vitamin_c_mg, multiplier),
            vitamin_d_mcg=self._scale_optional(nutrition_per_100g.vitamin_d_mcg, multiplier),
            folate_mcg_dfe=self._scale_optional(
                nutrition_per_100g.folate_mcg_dfe, multiplier
            ),
            energy_kj=derive_energy_kj(self._round(nutrition_per_100g.calories * multiplier)),
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

    @classmethod
    def _scale_optional(cls, value: Decimal | None, multiplier: Decimal) -> Decimal | None:
        return None if value is None else cls._round(value * multiplier)
