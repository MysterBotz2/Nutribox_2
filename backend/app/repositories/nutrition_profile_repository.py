from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nutrition_profile import NutritionProfile


class NutritionProfileRepository:
    """Persistence operations for one-to-one nutrition profiles."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, profile: NutritionProfile) -> None:
        self.session.add(profile)

    def get_by_user_id(self, user_id: int) -> NutritionProfile | None:
        return self.session.scalar(
            select(NutritionProfile).where(NutritionProfile.user_id == user_id)
        )
