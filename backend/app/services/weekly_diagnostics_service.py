from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal,ROUND_HALF_UP
from app.repositories.meal_repository import MealRepository
from app.repositories.scheduled_meal_repository import ScheduledMealRepository
from app.repositories.weight_entry_repository import WeightEntryRepository
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.schemas.weekly_diagnostics import *
from app.services.nutrient_calculator import PORTION_NUTRIENT_QUANTUM
class WeeklyDiagnosticsService:
 def __init__(self,m,s,w,t): self.m,self.s,self.w,self.t=m,s,w,t
 def weekly(self,user,week_start):
  if week_start.weekday()!=0: raise ValueError("week_start must be a Monday.")
  a=datetime.combine(week_start,time.min,tzinfo=timezone.utc);b=a+timedelta(days=7)
  meals=self.m.list_for_user_between(user,a,b); schedules=self.s.list_for_user(user,100000,0,a,b); weights=self.w.list(user,100000,0,a,b)[::-1]
  vals={"calories":sum((x.total_calories for x in meals),Decimal()),"protein_g":sum((x.total_protein_g for x in meals),Decimal()),"carbohydrates_g":sum((x.total_carbohydrates_g for x in meals),Decimal()),"fat_g":sum((x.total_fat_g for x in meals),Decimal()),"fiber_g":sum((x.total_fiber_g for x in meals),Decimal())}
  q=lambda x:x.quantize(PORTION_NUTRIENT_QUANTUM,rounding=ROUND_HALF_UP)
  nut={k:NutrientWeekMetric(total=q(v),daily_average=q(v/7)) for k,v in vals.items()}
  target=self.t.get_by_user_id(user)
  def tm(k):
   v=getattr(target,k) if target else None
   return WeeklyTargetMetric(reference=q(v*7) if v is not None else None,state="target_unavailable" if v is None else ("below_target" if vals[k]<v*7 else "met_or_above_target"))
  return WeeklyDiagnosticsResponse(period_start=a,period_end=b,meals_logged=len(meals),days_with_logged_meals=len({x.recorded_at.date() for x in meals}),days_in_period=7,logging_days_ratio=q(Decimal(len({x.recorded_at.date() for x in meals}))/7),scheduled_meals=len(schedules),days_with_scheduled_meals=len({x.scheduled_for.date() for x in schedules}),nutrition=nut,weight=WeeklyWeightSummary(first_weight_kg=weights[0].weight_kg if weights else None,latest_weight_kg=weights[-1].weight_kg if weights else None,weight_change_kg=q(weights[-1].weight_kg-weights[0].weight_kg) if len(weights)>1 else None),target_comparison=WeeklyTargetComparison(**{k:tm(k) for k in vals}))
