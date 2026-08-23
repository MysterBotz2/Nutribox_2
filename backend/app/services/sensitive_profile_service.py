from fastapi import HTTPException, status

from app.models.sensitive_profile_context import SensitiveProfileContext
from app.repositories.sensitive_profile_repository import SensitiveProfileRepository
from app.schemas.sensitive_profile import SensitiveProfileUpdateRequest
from app.services.profile_consent_service import ProfileConsentService


class SensitiveProfileService:
    """Owner-scoped sensitive declaration storage with consent enforcement."""

    def __init__(
        self,
        repository: SensitiveProfileRepository,
        consent_service: ProfileConsentService,
    ) -> None:
        self._contexts = repository
        self._consents = consent_service

    def get_context(self, user_id: int) -> SensitiveProfileContext | None:
        """Return data only while the owner has granted storage consent."""
        if not self._consents.storage_is_granted(user_id):
            return None
        return self._contexts.get_by_user_id(user_id)

    def replace_context(
        self, user_id: int, request: SensitiveProfileUpdateRequest
    ) -> SensitiveProfileContext:
        if not self._consents.storage_is_granted(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sensitive profile storage consent must be granted.",
            )
        session = self._contexts.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            context = self._contexts.get_by_user_id(user_id)
            if context is None:
                context = SensitiveProfileContext(user_id=user_id)
                self._contexts.add(context)
            for field, value in request.model_dump(mode="json").items():
                setattr(context, field, value)
            session.flush()
        return context
