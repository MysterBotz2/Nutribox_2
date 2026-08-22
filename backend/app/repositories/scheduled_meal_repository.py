from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduled_meal import ScheduledMeal


class ScheduledMealRepository:
    """Persistence operations for owner-filtered scheduled meal entries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, scheduled_meal: ScheduledMeal) -> None:
        self.session.add(scheduled_meal)

    def get_by_id_for_user(self, scheduled_meal_id: int, user_id: int) -> ScheduledMeal | None:
        statement = select(ScheduledMeal).where(
            ScheduledMeal.id == scheduled_meal_id,
            ScheduledMeal.user_id == user_id,
        )
        return self.session.scalar(statement)

    def list_for_user(
        self,
        user_id: int,
        limit: int,
        offset: int,
        scheduled_from: datetime | None = None,
        scheduled_to: datetime | None = None,
    ) -> list[ScheduledMeal]:
        statement = select(ScheduledMeal).where(ScheduledMeal.user_id == user_id)
        if scheduled_from is not None:
            statement = statement.where(ScheduledMeal.scheduled_for >= scheduled_from)
        if scheduled_to is not None:
            statement = statement.where(ScheduledMeal.scheduled_for <= scheduled_to)
        statement = (
            statement.order_by(ScheduledMeal.scheduled_for.asc(), ScheduledMeal.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def delete(self, scheduled_meal: ScheduledMeal) -> None:
        self.session.delete(scheduled_meal)
