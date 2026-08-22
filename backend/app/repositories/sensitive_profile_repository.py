from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sensitive_profile_context import SensitiveProfileContext


class SensitiveProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, context: SensitiveProfileContext) -> None:
        self.session.add(context)

    def get_by_user_id(self, user_id: int) -> SensitiveProfileContext | None:
        return self.session.scalar(
            select(SensitiveProfileContext).where(SensitiveProfileContext.user_id == user_id)
        )

    def delete(self, context: SensitiveProfileContext) -> None:
        self.session.delete(context)
