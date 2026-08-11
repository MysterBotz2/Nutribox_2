from datetime import date

from pydantic import BaseModel, Field

from app.schemas.nutrition import NutrientValues


class NutrientTotals(NutrientValues):
    """Stored-meal nutrient totals aggregated for a reporting period."""


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
