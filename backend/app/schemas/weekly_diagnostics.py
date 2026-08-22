from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.schemas.progress import NutrientTotals

class NutrientWeekMetric(BaseModel): total: Decimal; daily_average: Decimal
class WeeklyWeightSummary(BaseModel): first_weight_kg: Decimal|None; latest_weight_kg: Decimal|None; weight_change_kg: Decimal|None
class WeeklyTargetMetric(BaseModel): reference: Decimal|None; state: str
class WeeklyTargetComparison(BaseModel): calories:WeeklyTargetMetric; protein_g:WeeklyTargetMetric; carbohydrates_g:WeeklyTargetMetric; fat_g:WeeklyTargetMetric; fiber_g:WeeklyTargetMetric
class WeeklyDiagnosticsResponse(BaseModel):
 period_start:datetime; period_end:datetime; meals_logged:int; days_with_logged_meals:int; days_in_period:int; logging_days_ratio:Decimal; scheduled_meals:int; days_with_scheduled_meals:int; nutrition:dict[str,NutrientWeekMetric]; weight:WeeklyWeightSummary; target_comparison:WeeklyTargetComparison
