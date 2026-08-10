from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.meal import Meal


class MealRepository:
    """Persistence operations for meals and their owned item snapshots."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, meal: Meal) -> None:
        self.session.add(meal)

    def get_by_id_for_user(self, meal_id: int, user_id: int) -> Meal | None:
        statement = (
            select(Meal)
            .options(selectinload(Meal.items))
            .where(Meal.id == meal_id, Meal.user_id == user_id)
        )
        return self.session.scalar(statement)

    def list_for_user(self, user_id: int, limit: int, offset: int) -> list[Meal]:
        statement = (
            select(Meal)
            .options(selectinload(Meal.items))
            .where(Meal.user_id == user_id)
            .order_by(Meal.recorded_at.desc(), Meal.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))
