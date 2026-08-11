from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.nutrition import NutrientValues
from app.schemas.nutrition_target import TargetNutrientValues


class NutrientTotals(NutrientValues):
    """Stored-meal nutrient totals aggregated for a reporting period."""


class OptionalNutrientValues(BaseModel):
    """Nullable neutral comparison values; remaining amounts may be negative."""

    calories: Decimal | None
    protein_g: Decimal | None
    carbohydrates_g: Decimal | None
    fat_g: Decimal | None
    fiber_g: Decimal | None


class DailyProgressPoint(BaseModel):
    date: date
    meal_count: int
    totals: NutrientTotals


class DailyProgressResponse(DailyProgressPoint):
    pass


class WeeklyProgressResponse(BaseModel):
    week_start: date
    week_end: date
    meal_count: int
    totals: NutrientTotals
    daily: list[DailyProgressPoint] = Field(min_length=7, max_length=7)


class ProgressSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    meal_count: int
    days_with_meals: int
    totals: NutrientTotals
    daily_average: NutrientTotals
    daily: list[DailyProgressPoint]


class TargetStatusResponse(BaseModel):
    """Neutral numeric comparison of today's stored consumption and configured targets."""

    date: date
    meal_count: int
    consumed: NutrientTotals
    targets: TargetNutrientValues | None
    remaining: OptionalNutrientValues | None
    percent_of_target: OptionalNutrientValues | None
