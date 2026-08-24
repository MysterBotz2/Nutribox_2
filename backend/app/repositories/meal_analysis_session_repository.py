from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.meal_analysis_session import MealAnalysisSession


class MealAnalysisSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, item: MealAnalysisSession) -> None:
        self.session.add(item)

    def get_for_user(self, session_id: int, user_id: int, *, lock: bool = False) -> MealAnalysisSession | None:
        statement = select(MealAnalysisSession).where(MealAnalysisSession.id == session_id, MealAnalysisSession.user_id == user_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)
