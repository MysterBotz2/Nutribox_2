from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.meal import Meal
from app.repositories.meal_repository import MealRepository
from app.schemas.progress import (
    DailyProgressPoint,
    DailyProgressResponse,
    NutrientTotals,
    ProgressSummaryResponse,
    WeeklyProgressResponse,
)
from app.services.nutrient_calculator import PORTION_NUTRIENT_QUANTUM

ZERO = Decimal("0")


class InvalidTimezoneError(ValueError):
    """Raised for a timezone identifier unavailable to the standard library."""


def current_utc_datetime() -> datetime:
    """Small clock seam for deterministic tests of the today/summary routes."""
    return datetime.now(timezone.utc)


def resolve_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise InvalidTimezoneError("Timezone must be a valid IANA timezone identifier.") from error


class ProgressService:
    """Bounded, deterministic progress analytics from immutable Meal totals."""

    def __init__(self, meal_repository: MealRepository) -> None:
        self._meals = meal_repository

    def today(self, user_id: int, timezone_name: str) -> DailyProgressResponse:
        timezone_value = resolve_timezone(timezone_name)
        local_today = current_utc_datetime().astimezone(timezone_value).date()
        return self.daily(user_id, local_today, timezone_name)

    def daily(self, user_id: int, local_date: date, timezone_name: str) -> DailyProgressResponse:
        timezone_value = resolve_timezone(timezone_name)
        meals = self._meals_for_local_dates(user_id, local_date, local_date, timezone_value)
        return self._daily_point(local_date, meals)

    def weekly(
        self, user_id: int, week_start: date, timezone_name: str
    ) -> WeeklyProgressResponse:
        if week_start.weekday() != 0:
            raise ValueError("week_start must be a Monday.")
        week_end = week_start + timedelta(days=6)
        timezone_value = resolve_timezone(timezone_name)
        meals = self._meals_for_local_dates(user_id, week_start, week_end, timezone_value)
        daily = self._daily_series(week_start, 7, meals, timezone_value)
        return WeeklyProgressResponse(
            week_start=week_start,
            week_end=week_end,
            meal_count=sum(point.meal_count for point in daily),
            totals=self._sum_totals(point.totals for point in daily),
            daily=daily,
        )

    def summary(
        self, user_id: int, days: int, timezone_name: str
    ) -> ProgressSummaryResponse:
        timezone_value = resolve_timezone(timezone_name)
        period_end = current_utc_datetime().astimezone(timezone_value).date()
        period_start = period_end - timedelta(days=days - 1)
        meals = self._meals_for_local_dates(user_id, period_start, period_end, timezone_value)
        daily = self._daily_series(period_start, days, meals, timezone_value)
        totals = self._sum_totals(point.totals for point in daily)
        return ProgressSummaryResponse(
            period_start=period_start,
            period_end=period_end,
            meal_count=sum(point.meal_count for point in daily),
            days_with_meals=sum(point.meal_count > 0 for point in daily),
            totals=totals,
            daily_average=self._divide_totals(totals, days),
            daily=daily,
        )

    def _meals_for_local_dates(
        self, user_id: int, start_date: date, end_date: date, timezone_value: ZoneInfo
    ) -> list[Meal]:
        start_utc = self._local_midnight_to_utc(start_date, timezone_value)
        end_utc = self._local_midnight_to_utc(end_date + timedelta(days=1), timezone_value)
        return self._meals.list_for_user_between(user_id, start_utc, end_utc)

    @staticmethod
    def _local_midnight_to_utc(local_date: date, timezone_value: ZoneInfo) -> datetime:
        return datetime.combine(local_date, time.min, tzinfo=timezone_value).astimezone(timezone.utc)

    def _daily_series(
        self, start_date: date, days: int, meals: list[Meal], timezone_value: ZoneInfo
    ) -> list[DailyProgressPoint]:
        meals_by_date: dict[date, list[Meal]] = {}
        for meal in meals:
            local_date = meal.recorded_at.astimezone(timezone_value).date()
            meals_by_date.setdefault(local_date, []).append(meal)
        return [
            self._daily_point(start_date + timedelta(days=offset), meals_by_date.get(start_date + timedelta(days=offset), []))
            for offset in range(days)
        ]

    def _daily_point(self, local_date: date, meals: list[Meal]) -> DailyProgressPoint:
        return DailyProgressPoint(
            date=local_date,
            meal_count=len(meals),
            totals=self._sum_totals(self._meal_totals(meal) for meal in meals),
        )

    @staticmethod
    def _meal_totals(meal: Meal) -> NutrientTotals:
        return NutrientTotals(
            calories=meal.total_calories,
            protein_g=meal.total_protein_g,
            carbohydrates_g=meal.total_carbohydrates_g,
            fat_g=meal.total_fat_g,
            fiber_g=meal.total_fiber_g,
        )

    @staticmethod
    def _sum_totals(totals: object) -> NutrientTotals:
        materialized_totals = list(totals)
        return NutrientTotals(
            calories=ProgressService._total(item.calories for item in materialized_totals),
            protein_g=ProgressService._total(item.protein_g for item in materialized_totals),
            carbohydrates_g=ProgressService._total(
                item.carbohydrates_g for item in materialized_totals
            ),
            fat_g=ProgressService._total(item.fat_g for item in materialized_totals),
            fiber_g=ProgressService._total(item.fiber_g for item in materialized_totals),
        )

    @staticmethod
    def _total(values: object) -> Decimal:
        return sum(values, ZERO).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _divide_totals(totals: NutrientTotals, divisor: int) -> NutrientTotals:
        return NutrientTotals(
            calories=(totals.calories / divisor).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP),
            protein_g=(totals.protein_g / divisor).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP),
            carbohydrates_g=(totals.carbohydrates_g / divisor).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP),
            fat_g=(totals.fat_g / divisor).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP),
            fiber_g=(totals.fiber_g / divisor).quantize(PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP),
        )
