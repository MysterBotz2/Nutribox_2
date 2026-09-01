from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.models.leftover_scan import LeftoverScan
from app.models.meal import Meal
from app.repositories.leftover_scan_repository import LeftoverScanRepository
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.schemas.meal_analysis_session import MealAnalysisSessionState
from app.schemas.nutrition import PortionNutrition
from app.services.meal_analysis_session_service import (
    MealAnalysisSessionConsumedError,
    MealAnalysisSessionExpiredError,
    MealAnalysisSessionNotFoundError,
)
from app.services.nutrient_calculator import PORTION_NUTRIENT_QUANTUM


class LeftoverScanConflictError(ValueError):
    pass


class LeftoverScanSessionNotCompletedError(ValueError):
    pass


class LeftoverScanMealWeightUnavailableError(ValueError):
    pass


_CORE_FIELDS = {
    "calories": "total_calories",
    "protein_g": "total_protein_g",
    "carbohydrates_g": "total_carbohydrates_g",
    "fat_g": "total_fat_g",
    "fiber_g": "total_fiber_g",
}
_OPTIONAL_ITEM_FIELDS = {
    "saturated_fat_g": "calculated_saturated_fat_g",
    "sugars_g": "calculated_sugars_g",
    "sodium_mg": "calculated_sodium_mg",
    "cholesterol_mg": "calculated_cholesterol_mg",
    "omega_3_g": "calculated_omega_3_g",
    "omega_6_g": "calculated_omega_6_g",
    "calcium_mg": "calculated_calcium_mg",
    "potassium_mg": "calculated_potassium_mg",
    "zinc_mg": "calculated_zinc_mg",
    "iron_mg": "calculated_iron_mg",
    "magnesium_mg": "calculated_magnesium_mg",
    "phosphorus_mg": "calculated_phosphorus_mg",
    "vitamin_b6_mg": "calculated_vitamin_b6_mg",
    "niacin_mg": "calculated_niacin_mg",
    "vitamin_a_mcg_rae": "calculated_vitamin_a_mcg_rae",
    "vitamin_b12_mcg": "calculated_vitamin_b12_mcg",
    "vitamin_c_mg": "calculated_vitamin_c_mg",
    "vitamin_d_mcg": "calculated_vitamin_d_mcg",
    "folate_mcg_dfe": "calculated_folate_mcg_dfe",
}
_SNAPSHOT_FIELDS = tuple((*_CORE_FIELDS.keys(), *_OPTIONAL_ITEM_FIELDS.keys()))


class LeftoverScanService:
    """Persist account-linked leftover estimates from an already calculated session."""

    def __init__(self, repository: LeftoverScanRepository) -> None:
        self._repository = repository

    def create_from_completed_session(
        self, *, meal: Meal, analysis_session_id: int, user_id: int
    ) -> LeftoverScan:
        session = self._repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            if meal.measured_weight_grams is None or meal.measured_weight_grams <= 0:
                raise LeftoverScanMealWeightUnavailableError(
                    "The original meal does not have a positive measured weight."
                )
            analysis_session = MealAnalysisSessionRepository(session).get_for_user(
                analysis_session_id, user_id, lock=True
            )
            if analysis_session is None:
                raise MealAnalysisSessionNotFoundError("Meal analysis session was not found.")
            if analysis_session.consumed_at is not None:
                raise MealAnalysisSessionConsumedError("Meal analysis session was already consumed.")
            if datetime.now(timezone.utc) >= analysis_session.expires_at:
                raise MealAnalysisSessionExpiredError("Meal analysis session has expired.")
            if analysis_session.status != "calculated":
                raise LeftoverScanSessionNotCompletedError(
                    "Meal analysis session is not completed."
                )
            if self._repository.get_by_analysis_session_id(analysis_session_id) is not None:
                raise LeftoverScanConflictError("Meal analysis session was already recorded as a leftover scan.")

            state = MealAnalysisSessionState.model_validate(analysis_session.state)
            remaining_weight = state.measured_weight_grams
            original_weight = meal.measured_weight_grams
            if remaining_weight > original_weight:
                raise LeftoverScanConflictError(
                    "Remaining weight cannot exceed the original meal weight."
                )

            original = self._original_snapshot(meal)
            remaining = self._session_snapshot(state)
            consumed, warnings = self._subtract_snapshots(original, remaining)
            consumed_weight = (original_weight - remaining_weight).quantize(
                PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP
            )
            percentage = ((consumed_weight / original_weight) * Decimal("100")).quantize(
                PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP
            )
            scan = LeftoverScan(
                meal_id=meal.id,
                analysis_session_id=analysis_session.id,
                original_weight_grams=original_weight,
                remaining_weight_grams=remaining_weight,
                consumed_weight_grams=consumed_weight,
                consumed_portion_percentage=percentage,
                remaining_nutrition_snapshot=self._serializable_snapshot(remaining),
                consumed_nutrition_snapshot=self._serializable_snapshot(consumed),
                comparison_warnings=warnings,
            )
            self._repository.add(scan)
            session.flush()
            analysis_session.consumed_at = datetime.now(timezone.utc)
            session.flush()
        return scan

    @staticmethod
    def _original_snapshot(meal: Meal) -> dict[str, Decimal | None]:
        snapshot: dict[str, Decimal | None] = {
            nutrient: getattr(meal, field) for nutrient, field in _CORE_FIELDS.items()
        }
        for nutrient, item_field in _OPTIONAL_ITEM_FIELDS.items():
            values = [getattr(item, item_field) for item in meal.items]
            snapshot[nutrient] = (
                sum(values, Decimal("0")) if values and all(value is not None for value in values) else None
            )
        return snapshot

    @staticmethod
    def _session_snapshot(state: MealAnalysisSessionState) -> dict[str, Decimal | None]:
        snapshot: dict[str, Decimal | None] = {}
        for nutrient in _SNAPSHOT_FIELDS:
            values: list[Decimal | None] = []
            for component in state.components:
                if component.nutrition is None:
                    raise LeftoverScanSessionNotCompletedError("Meal analysis session is incomplete.")
                value = component.nutrition.get(nutrient)
                values.append(Decimal(value) if value is not None else None)
            snapshot[nutrient] = (
                sum(values, Decimal("0")) if values and all(value is not None for value in values) else None
            )
        return snapshot

    @staticmethod
    def _subtract_snapshots(
        original: dict[str, Decimal | None], remaining: dict[str, Decimal | None]
    ) -> tuple[dict[str, Decimal | None], list[dict[str, str]]]:
        consumed: dict[str, Decimal | None] = {}
        warnings: list[dict[str, str]] = []
        for nutrient in _SNAPSHOT_FIELDS:
            initial = original[nutrient]
            leftover = remaining[nutrient]
            if initial is None or leftover is None:
                consumed[nutrient] = None
                continue
            value = initial - leftover
            if value < 0:
                consumed[nutrient] = Decimal("0")
                warnings.append({"nutrient": nutrient, "code": "remaining_exceeds_original"})
            else:
                consumed[nutrient] = value.quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP)
        return consumed, warnings

    @staticmethod
    def _serializable_snapshot(snapshot: dict[str, Decimal | None]) -> dict[str, str | None]:
        # energy_kj is deliberately omitted: PortionNutrition derives it from calories.
        return {key: str(value) if value is not None else None for key, value in snapshot.items()}

    @staticmethod
    def response_nutrition(snapshot: dict) -> PortionNutrition:
        return PortionNutrition(**snapshot)
