from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.meal_repository import MealRepository
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.schemas.progress import (
    DailyProgressResponse,
    ProgressSummaryResponse,
    WeeklyProgressResponse,
    TargetStatusResponse,
)
from app.services.nutrition_target_comparison_service import NutritionTargetComparisonService
from app.services.progress_service import InvalidTimezoneError, ProgressService
from app.repositories.scheduled_meal_repository import ScheduledMealRepository
from app.repositories.weight_entry_repository import WeightEntryRepository
from app.schemas.weekly_diagnostics import WeeklyDiagnosticsResponse
from app.services.weekly_diagnostics_service import WeeklyDiagnosticsService

router = APIRouter(prefix="/api/progress", tags=["progress"])


def get_progress_service(database_session: Annotated[Session, Depends(get_db)]) -> ProgressService:
    return ProgressService(MealRepository(database_session))


def get_target_comparison_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> NutritionTargetComparisonService:
    return NutritionTargetComparisonService(
        ProgressService(MealRepository(database_session)),
        NutritionTargetRepository(database_session),
    )


def _progress_error(error: ValueError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))

@router.get("/weekly-diagnostics", response_model=WeeklyDiagnosticsResponse)
def weekly_diagnostics(week_start: date, current_user: Annotated[User, Depends(get_current_user)], database_session: Annotated[Session, Depends(get_db)]):
    try:
        return WeeklyDiagnosticsService(MealRepository(database_session), ScheduledMealRepository(database_session), WeightEntryRepository(database_session), NutritionTargetRepository(database_session)).weekly(current_user.id, week_start)
    except ValueError as error:
        raise _progress_error(error) from None


@router.get("/today", response_model=DailyProgressResponse)
def get_today_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    progress_service: Annotated[ProgressService, Depends(get_progress_service)],
    timezone: str = Query("UTC", min_length=1, max_length=64),
) -> DailyProgressResponse:
    try:
        return progress_service.today(current_user.id, timezone)
    except InvalidTimezoneError as error:
        raise _progress_error(error) from None


@router.get("/target-status", response_model=TargetStatusResponse)
def get_today_target_status(
    current_user: Annotated[User, Depends(get_current_user)],
    comparison_service: Annotated[
        NutritionTargetComparisonService, Depends(get_target_comparison_service)
    ],
    timezone: str = Query("UTC", min_length=1, max_length=64),
) -> TargetStatusResponse:
    try:
        return comparison_service.today_status(current_user.id, timezone)
    except InvalidTimezoneError as error:
        raise _progress_error(error) from None


@router.get("/daily", response_model=DailyProgressResponse)
def get_daily_progress(
    date: date,
    current_user: Annotated[User, Depends(get_current_user)],
    progress_service: Annotated[ProgressService, Depends(get_progress_service)],
    timezone: str = Query("UTC", min_length=1, max_length=64),
) -> DailyProgressResponse:
    try:
        return progress_service.daily(current_user.id, date, timezone)
    except InvalidTimezoneError as error:
        raise _progress_error(error) from None


@router.get("/weekly", response_model=WeeklyProgressResponse)
def get_weekly_progress(
    week_start: date,
    current_user: Annotated[User, Depends(get_current_user)],
    progress_service: Annotated[ProgressService, Depends(get_progress_service)],
    timezone: str = Query("UTC", min_length=1, max_length=64),
) -> WeeklyProgressResponse:
    try:
        return progress_service.weekly(current_user.id, week_start, timezone)
    except (InvalidTimezoneError, ValueError) as error:
        raise _progress_error(error) from None


@router.get("/summary", response_model=ProgressSummaryResponse)
def get_progress_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    progress_service: Annotated[ProgressService, Depends(get_progress_service)],
    days: int = Query(30, ge=1, le=365),
    timezone: str = Query("UTC", min_length=1, max_length=64),
) -> ProgressSummaryResponse:
    try:
        return progress_service.summary(current_user.id, days, timezone)
    except InvalidTimezoneError as error:
        raise _progress_error(error) from None
