from app.models.profile_consent import ProfileConsent
from app.repositories.profile_consent_repository import ProfileConsentRepository
from app.repositories.sensitive_profile_repository import SensitiveProfileRepository
from app.schemas.sensitive_profile import ProfileConsentState, ProfileConsentUpdateRequest


class ProfileConsentService:
    """Manage product-level permission states and their immediate effects."""

    def __init__(
        self,
        consent_repository: ProfileConsentRepository,
        sensitive_profile_repository: SensitiveProfileRepository,
    ) -> None:
        self._consents = consent_repository
        self._sensitive_profiles = sensitive_profile_repository

    def get_consent(self, user_id: int) -> ProfileConsent | None:
        return self._consents.get_by_user_id(user_id)

    def storage_is_granted(self, user_id: int) -> bool:
        consent = self.get_consent(user_id)
        return consent is not None and consent.sensitive_storage == ProfileConsentState.GRANTED.value

    def replace_consent(self, user_id: int, request: ProfileConsentUpdateRequest) -> ProfileConsent:
        session = self._consents.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            consent = self._consents.get_by_user_id(user_id)
            if consent is None:
                consent = ProfileConsent(user_id=user_id)
                self._consents.add(consent)
            consent.sensitive_storage = request.sensitive_storage.value
            consent.personalization = request.personalization.value
            consent.ai_context = request.ai_context.value
            if request.sensitive_storage is ProfileConsentState.WITHDRAWN:
                context = self._sensitive_profiles.get_by_user_id(user_id)
                if context is not None:
                    self._sensitive_profiles.delete(context)
            session.flush()
        return consent
