from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nutrition_target import NutritionTarget


class NutritionTargetRepository:
    """Persistence operations for one explicit target set per user."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, target: NutritionTarget) -> None:
        self.session.add(target)

    def get_by_user_id(self, user_id: int) -> NutritionTarget | None:
        return self.session.scalar(select(NutritionTarget).where(NutritionTarget.user_id == user_id))
