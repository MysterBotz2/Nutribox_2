from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile_consent import ProfileConsent


class ProfileConsentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, consent: ProfileConsent) -> None:
        self.session.add(consent)

    def get_by_user_id(self, user_id: int) -> ProfileConsent | None:
        return self.session.scalar(select(ProfileConsent).where(ProfileConsent.user_id == user_id))
