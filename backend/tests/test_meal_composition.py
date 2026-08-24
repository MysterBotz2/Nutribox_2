from decimal import Decimal
from uuid import UUID

import pytest

from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
    WeightSource,
)
from app.services.meal_composition_service import allocate_component_weights


def test_allocator_normalizes_and_reconciles_exactly() -> None:
    result = allocate_component_weights(Decimal("500.000"), [Decimal(".5"), Decimal(".3"), Decimal(".2")])
    assert [item.estimated_weight_grams for item in result] == [Decimal("250.000"), Decimal("150.000"), Decimal("100.000")]
    assert sum((item.estimated_weight_grams for item in result), Decimal()) == Decimal("500.000")


@pytest.mark.parametrize("weight,shares", [(Decimal("100.000"), [Decimal(1)] * 3), (Decimal("101.000"), [Decimal(1)] * 3)])
def test_allocator_largest_remainder_is_stable(weight: Decimal, shares: list[Decimal]) -> None:
    first = allocate_component_weights(weight, shares)
    assert first == allocate_component_weights(weight, shares)
    assert sum((item.estimated_weight_grams for item in first), Decimal()) == weight
    assert all(item.estimated_weight_grams.as_tuple().exponent >= -3 for item in first)


@pytest.mark.parametrize("shares", [[Decimal(0), Decimal(0)], [Decimal("-1"), Decimal("1")], [Decimal("NaN")], [Decimal("Infinity")], [Decimal("-Infinity")]])
def test_allocator_rejects_invalid_proportions(shares: list[Decimal]) -> None:
    with pytest.raises(ValueError):
        allocate_component_weights(Decimal("100.000"), shares)


def test_session_state_serializes_decimals_as_strings() -> None:
    state = MealAnalysisSessionState(measured_weight_grams=Decimal("150.000"), components=[MealAnalysisSessionComponent(recognized_name="Rice", raw_estimated_proportion=Decimal(".5"), normalized_proportion=Decimal(".5"), estimated_weight_grams=Decimal("150.000"), resolution_status=ComponentResolutionStatus.RESOLVED, weight_source=WeightSource.AI_ESTIMATE, nutrition=None)])
    encoded = state.model_dump(mode="json")
    assert encoded["measured_weight_grams"] == "150.000"
    assert isinstance(encoded["components"][0]["component_id"], str)
    assert MealAnalysisSessionState.model_validate(encoded).measured_weight_grams == Decimal("150.000")


def test_allocator_zero_share_is_preserved_and_all_outputs_are_quantized() -> None:
    result = allocate_component_weights(Decimal("101.000"), [Decimal("0"), Decimal("1"), Decimal("1")])
    assert [item.estimated_weight_grams for item in result] == [Decimal("0.000"), Decimal("50.500"), Decimal("50.500")]
    assert sum((item.estimated_weight_grams for item in result), Decimal()) == Decimal("101.000")
    assert all(item.estimated_weight_grams.as_tuple().exponent == -3 for item in result)


def test_allocator_rejects_unsupported_weight_precision_and_is_repeatable() -> None:
    with pytest.raises(ValueError):
        allocate_component_weights(Decimal("100.0001"), [Decimal("1")])
    expected = allocate_component_weights(Decimal("101.000"), [Decimal("1"), Decimal("1"), Decimal("1")])
    assert all(allocate_component_weights(Decimal("101.000"), [Decimal("1"), Decimal("1"), Decimal("1")]) == expected for _ in range(20))


def test_session_schema_validates_ids_versions_enums_and_unknown_values() -> None:
    component = MealAnalysisSessionComponent(
        component_id="7208c85b-d8b8-4bb8-9966-81b4b6ebcf5a",
        recognized_name="Rice",
        raw_estimated_proportion=Decimal("0.500"),
        normalized_proportion=Decimal("0.500"),
        estimated_weight_grams=Decimal("150.000"),
        resolution_status=ComponentResolutionStatus.RESOLVED,
        weight_source=WeightSource.MEASURED,
        candidates=[],
        nutrition={"sodium_mg": None, "fiber_g": "0.000"},
    )
    assert isinstance(component.component_id, UUID)
    assert component.candidates == []
    assert component.nutrition == {"sodium_mg": None, "fiber_g": "0.000"}
    state = MealAnalysisSessionState(measured_weight_grams=Decimal("150.000"), components=[component])
    assert state.version == 1
    with pytest.raises(ValueError):
        MealAnalysisSessionComponent(component_id="not-a-uuid", recognized_name="Rice", raw_estimated_proportion=Decimal("1"), normalized_proportion=Decimal("1"), estimated_weight_grams=Decimal("1"), resolution_status=ComponentResolutionStatus.RESOLVED)
    with pytest.raises(ValueError):
        MealAnalysisSessionState(version=2, measured_weight_grams=Decimal("150"), components=[component])
    with pytest.raises(ValueError):
        MealAnalysisSessionComponent(recognized_name="Rice", raw_estimated_proportion=Decimal("1"), normalized_proportion=Decimal("1"), estimated_weight_grams=Decimal("1"), resolution_status=ComponentResolutionStatus.RESOLVED, weight_source="guess")
