from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.meal_analysis_session import MealAnalysisSession
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.schemas.meal_analysis_session import MealAnalysisSessionState


class MealAnalysisSessionNotFoundError(ValueError): pass
class MealAnalysisSessionExpiredError(ValueError): pass
class MealAnalysisSessionConsumedError(ValueError): pass


class MealAnalysisSessionService:
    def __init__(self, repository: MealAnalysisSessionRepository) -> None:
        self._repository = repository

    def create_session(self, user_id: int, state: MealAnalysisSessionState, status: str) -> MealAnalysisSession:
        now = datetime.now(timezone.utc)
        item = MealAnalysisSession(user_id=user_id, state=state.model_dump(mode="json"), status=status, expires_at=now + timedelta(minutes=settings.meal_analysis_session_ttl_minutes))
        self._repository.add(item); self._repository.session.flush()
        return item

    def get_session_for_user(self, session_id: int, user_id: int, *, lock: bool = False) -> MealAnalysisSession:
        item = self._repository.get_for_user(session_id, user_id, lock=lock)
        if item is None: raise MealAnalysisSessionNotFoundError("Meal analysis session was not found.")
        if item.consumed_at is not None: raise MealAnalysisSessionConsumedError("Meal analysis session was already consumed.")
        if datetime.now(timezone.utc) >= item.expires_at: raise MealAnalysisSessionExpiredError("Meal analysis session has expired.")
        return item

    def update_session_state(
        self, session_id: int, user_id: int, state: MealAnalysisSessionState, status: str
    ) -> MealAnalysisSession:
        item = self.get_session_for_user(session_id, user_id, lock=True)
        item.state = state.model_dump(mode="json")
        item.status = status
        self._repository.session.flush()
        return item

    def consume_session(self, session_id: int, user_id: int) -> MealAnalysisSession:
        item = self.get_session_for_user(session_id, user_id, lock=True)
        item.consumed_at = datetime.now(timezone.utc)
        self._repository.session.flush()
        return item
