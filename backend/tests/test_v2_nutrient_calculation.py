from decimal import Decimal

import pytest

from app.services.nutrient_calculator import ExtendedNutritionPer100g, NutrientCalculator


def make_v2_reference(**overrides: Decimal | None) -> ExtendedNutritionPer100g:
    values: dict[str, Decimal | None] = {
        "calories": Decimal("100.00"),
        "protein_g": Decimal("10.000"),
        "carbohydrates_g": Decimal("20.000"),
        "fat_g": Decimal("3.000"),
        "fiber_g": Decimal("2.000"),
        "saturated_fat_g": Decimal("1.2345"),
        "sugars_g": Decimal("0"),
        "sodium_mg": Decimal("123.456"),
        "cholesterol_mg": Decimal("12.000"),
        "omega_3_g": Decimal("0.500"),
        "omega_6_g": Decimal("1.500"),
        "calcium_mg": Decimal("12.345"),
        "potassium_mg": Decimal("100.000"),
        "zinc_mg": Decimal("1.000"),
        "iron_mg": Decimal("2.000"),
        "magnesium_mg": Decimal("3.000"),
        "phosphorus_mg": Decimal("50.000"),
        "vitamin_b6_mg": Decimal("0.400"),
        "niacin_mg": Decimal("2.000"),
        "vitamin_a_mcg_rae": Decimal("4.000"),
        "vitamin_b12_mcg": Decimal("0.500"),
        "vitamin_c_mg": Decimal("5.000"),
        "vitamin_d_mcg": Decimal("0.250"),
        "folate_mcg_dfe": Decimal("6.000"),
    }
    values.update(overrides)
    return ExtendedNutritionPer100g(**values)  # type: ignore[arg-type]


def test_extended_calculator_scales_mandatory_v2_nutrients() -> None:
    result = NutrientCalculator().calculate_extended(make_v2_reference(), Decimal("125.5"))

    assert result.calories == Decimal("125.500")
    assert result.protein_g == Decimal("12.550")
    assert result.carbohydrates_g == Decimal("25.100")
    assert result.fat_g == Decimal("3.765")
    assert result.fiber_g == Decimal("2.510")
    assert result.saturated_fat_g == Decimal("1.549")
    assert result.sugars_g == Decimal("0.000")
    assert result.sodium_mg == Decimal("154.937")
    assert result.cholesterol_mg == Decimal("15.060")
    assert result.phosphorus_mg == Decimal("62.750")
    assert result.vitamin_b6_mg == Decimal("0.502")
    assert result.niacin_mg == Decimal("2.510")
    assert result.energy_kj == Decimal("525.092")


def test_extended_calculator_scales_optional_values_and_propagates_unknowns() -> None:
    result = NutrientCalculator().calculate_extended(
        make_v2_reference(omega_3_g=None, calcium_mg=Decimal("12.345")), Decimal("125.5")
    )

    assert result.omega_3_g is None
    assert result.calcium_mg == Decimal("15.493")
    assert result.vitamin_b12_mcg == Decimal("0.628")


def test_extended_calculator_preserves_unknown_at_zero_weight() -> None:
    result = NutrientCalculator().calculate_extended(
        make_v2_reference(sodium_mg=None, sugars_g=Decimal("0")), Decimal("0")
    )

    assert result.sodium_mg is None
    assert result.sugars_g == Decimal("0.000")


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
def test_extended_calculator_rejects_invalid_weight_before_calculation(value: Decimal) -> None:
    with pytest.raises(ValueError):
        NutrientCalculator().calculate_extended(make_v2_reference(), value)
