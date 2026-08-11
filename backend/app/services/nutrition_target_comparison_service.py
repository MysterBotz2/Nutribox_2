from decimal import Decimal, ROUND_HALF_UP

from app.models.nutrition_target import NutritionTarget
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.schemas.nutrition_target import TargetNutrientValues
from app.schemas.progress import OptionalNutrientValues, TargetStatusResponse
from app.schemas.progress import DailyProgressResponse
from app.services.nutrient_calculator import PORTION_NUTRIENT_QUANTUM
from app.services.progress_service import ProgressService


class NutritionTargetComparisonService:
    """Deterministic, neutral comparison of stored progress and explicit targets."""

    def __init__(
        self,
        progress_service: ProgressService,
        target_repository: NutritionTargetRepository,
    ) -> None:
        self._progress = progress_service
        self._targets = target_repository

    def today_status(self, user_id: int, timezone_name: str) -> TargetStatusResponse:
        progress = self._progress.today(user_id, timezone_name)
        return self.status_for_today_progress(user_id, progress)

    def status_for_today_progress(
        self, user_id: int, progress: DailyProgressResponse
    ) -> TargetStatusResponse:
        """Compare an already assembled trusted today-progress result with the user's target."""
        target = self._targets.get_by_user_id(user_id)
        if target is None:
            return TargetStatusResponse(
                date=progress.date,
                meal_count=progress.meal_count,
                consumed=progress.totals,
                targets=None,
                remaining=None,
                percent_of_target=None,
            )
        targets = self._target_values(target)
        return TargetStatusResponse(
            date=progress.date,
            meal_count=progress.meal_count,
            consumed=progress.totals,
            targets=targets,
            remaining=OptionalNutrientValues(
                calories=self._remaining(targets.calories, progress.totals.calories),
                protein_g=self._remaining(targets.protein_g, progress.totals.protein_g),
                carbohydrates_g=self._remaining(
                    targets.carbohydrates_g, progress.totals.carbohydrates_g
                ),
                fat_g=self._remaining(targets.fat_g, progress.totals.fat_g),
                fiber_g=self._remaining(targets.fiber_g, progress.totals.fiber_g),
            ),
            percent_of_target=OptionalNutrientValues(
                calories=self._percent(targets.calories, progress.totals.calories),
                protein_g=self._percent(targets.protein_g, progress.totals.protein_g),
                carbohydrates_g=self._percent(
                    targets.carbohydrates_g, progress.totals.carbohydrates_g
                ),
                fat_g=self._percent(targets.fat_g, progress.totals.fat_g),
                fiber_g=self._percent(targets.fiber_g, progress.totals.fiber_g),
            ),
        )

    @staticmethod
    def _target_values(target: NutritionTarget) -> TargetNutrientValues:
        return TargetNutrientValues(
            calories=target.calories,
            protein_g=target.protein_g,
            carbohydrates_g=target.carbohydrates_g,
            fat_g=target.fat_g,
            fiber_g=target.fiber_g,
        )

    @staticmethod
    def _remaining(target: Decimal | None, consumed: Decimal) -> Decimal | None:
        if target is None:
            return None
        return (target - consumed).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _percent(target: Decimal | None, consumed: Decimal) -> Decimal | None:
        if target is None:
            return None
        return (consumed / target * Decimal("100")).quantize(
            PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP
        )
