from datetime import datetime

from app.models.scheduled_meal import ScheduledMeal
from app.repositories.scheduled_meal_repository import ScheduledMealRepository
from app.schemas.scheduled_meal import ScheduledMealWriteRequest


class ScheduledMealService:
    """Transactional CRUD for planned intent, separate from actual meals."""

    def __init__(self, scheduled_meal_repository: ScheduledMealRepository) -> None:
        self._scheduled_meal_repository = scheduled_meal_repository

    def create_scheduled_meal(
        self, request: ScheduledMealWriteRequest, user_id: int
    ) -> ScheduledMeal:
        session = self._scheduled_meal_repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            scheduled_meal = ScheduledMeal(user_id=user_id, **request.model_dump())
            self._scheduled_meal_repository.add(scheduled_meal)
            session.flush()
        return scheduled_meal

    def get_scheduled_meal(self, scheduled_meal_id: int, user_id: int) -> ScheduledMeal | None:
        return self._scheduled_meal_repository.get_by_id_for_user(scheduled_meal_id, user_id)

    def list_scheduled_meals(
        self,
        user_id: int,
        limit: int,
        offset: int,
        scheduled_from: datetime | None,
        scheduled_to: datetime | None,
    ) -> list[ScheduledMeal]:
        return self._scheduled_meal_repository.list_for_user(
            user_id, limit, offset, scheduled_from, scheduled_to
        )

    def update_scheduled_meal(
        self, scheduled_meal: ScheduledMeal, request: ScheduledMealWriteRequest
    ) -> ScheduledMeal:
        session = self._scheduled_meal_repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            for field, value in request.model_dump().items():
                setattr(scheduled_meal, field, value)
            session.flush()
        return scheduled_meal

    def delete_scheduled_meal(self, scheduled_meal: ScheduledMeal) -> None:
        session = self._scheduled_meal_repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            self._scheduled_meal_repository.delete(scheduled_meal)
            session.flush()
