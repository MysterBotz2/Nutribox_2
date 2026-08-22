from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.scheduled_meal_repository import ScheduledMealRepository
from app.schemas.scheduled_meal import (
    ScheduledMealCreateRequest,
    ScheduledMealListResponse,
    ScheduledMealResponse,
    ScheduledMealUpdateRequest,
)
from app.services.scheduled_meal_service import ScheduledMealService

router = APIRouter(prefix="/api/scheduled-meals", tags=["scheduled meals"])


def get_scheduled_meal_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> ScheduledMealService:
    return ScheduledMealService(ScheduledMealRepository(database_session))


def _validate_window(
    scheduled_from: datetime | None, scheduled_to: datetime | None
) -> None:
    for value in (scheduled_from, scheduled_to):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Schedule window timestamps must include a timezone offset.",
            )
    if scheduled_from is not None and scheduled_to is not None and scheduled_from > scheduled_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="scheduled_from must be earlier than or equal to scheduled_to.",
        )


@router.post("", response_model=ScheduledMealResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_meal(
    request: ScheduledMealCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    scheduled_meal_service: Annotated[ScheduledMealService, Depends(get_scheduled_meal_service)],
) -> ScheduledMealResponse:
    return scheduled_meal_service.create_scheduled_meal(request, current_user.id)


@router.get("", response_model=ScheduledMealListResponse)
def list_scheduled_meals(
    current_user: Annotated[User, Depends(get_current_user)],
    scheduled_meal_service: Annotated[ScheduledMealService, Depends(get_scheduled_meal_service)],
    scheduled_from: datetime | None = Query(default=None),
    scheduled_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ScheduledMealListResponse:
    _validate_window(scheduled_from, scheduled_to)
    return ScheduledMealListResponse(
        scheduled_meals=scheduled_meal_service.list_scheduled_meals(
            current_user.id, limit, offset, scheduled_from, scheduled_to
        ),
        limit=limit,
        offset=offset,
    )


@router.get("/{scheduled_meal_id}", response_model=ScheduledMealResponse)
def get_scheduled_meal(
    scheduled_meal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    scheduled_meal_service: Annotated[ScheduledMealService, Depends(get_scheduled_meal_service)],
) -> ScheduledMealResponse:
    scheduled_meal = scheduled_meal_service.get_scheduled_meal(scheduled_meal_id, current_user.id)
    if scheduled_meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled meal was not found.")
    return scheduled_meal


@router.put("/{scheduled_meal_id}", response_model=ScheduledMealResponse)
def update_scheduled_meal(
    scheduled_meal_id: int,
    request: ScheduledMealUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    scheduled_meal_service: Annotated[ScheduledMealService, Depends(get_scheduled_meal_service)],
) -> ScheduledMealResponse:
    scheduled_meal = scheduled_meal_service.get_scheduled_meal(scheduled_meal_id, current_user.id)
    if scheduled_meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled meal was not found.")
    return scheduled_meal_service.update_scheduled_meal(scheduled_meal, request)


@router.delete("/{scheduled_meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_meal(
    scheduled_meal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    scheduled_meal_service: Annotated[ScheduledMealService, Depends(get_scheduled_meal_service)],
) -> Response:
    scheduled_meal = scheduled_meal_service.get_scheduled_meal(scheduled_meal_id, current_user.id)
    if scheduled_meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled meal was not found.")
    scheduled_meal_service.delete_scheduled_meal(scheduled_meal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
