from app.models.nutrition_profile import NutritionProfile
from app.models.sensitive_profile_context import SensitiveProfileContext
from app.repositories.nutrition_profile_repository import NutritionProfileRepository
from app.repositories.sensitive_profile_repository import SensitiveProfileRepository
from app.schemas.onboarding import OnboardingRequiredField, OnboardingStatusResponse
from app.services.profile_consent_service import ProfileConsentService


class OnboardingService:
    """Derive mobile onboarding completeness from authoritative current state."""

    def __init__(
        self,
        profile_repository: NutritionProfileRepository,
        sensitive_profile_repository: SensitiveProfileRepository,
        consent_service: ProfileConsentService,
    ) -> None:
        self._profiles = profile_repository
        self._sensitive_profiles = sensitive_profile_repository
        self._consents = consent_service

    def status_for_user(self, user_id: int) -> OnboardingStatusResponse:
        profile = self._profiles.get_by_user_id(user_id)
        context = self._sensitive_profiles.get_by_user_id(user_id)
        missing = self._missing_ordinary(profile)
        missing.extend(self._missing_sensitive(context, self._consents.storage_is_granted(user_id)))
        return OnboardingStatusResponse(completed=not missing, missing_required_fields=missing)

    @staticmethod
    def _missing_ordinary(profile: NutritionProfile | None) -> list[OnboardingRequiredField]:
        if profile is None:
            return [
                OnboardingRequiredField.ALLERGIES,
                OnboardingRequiredField.LIFESTYLE_DIETS,
                OnboardingRequiredField.ACTIVITY_LEVEL,
                OnboardingRequiredField.BUDGET_ALLOTMENT,
                OnboardingRequiredField.NUTRITION_GOAL,
            ]
        missing: list[OnboardingRequiredField] = []
        # The existing list contract treats [] as an explicit "none selected" declaration.
        if profile.allergies is None:
            missing.append(OnboardingRequiredField.ALLERGIES)
        if profile.dietary_restrictions is None:
            missing.append(OnboardingRequiredField.LIFESTYLE_DIETS)
        if profile.activity_level is None:
            missing.append(OnboardingRequiredField.ACTIVITY_LEVEL)
        if profile.budget_allotment is None:
            missing.append(OnboardingRequiredField.BUDGET_ALLOTMENT)
        if profile.nutrition_goal is None:
            missing.append(OnboardingRequiredField.NUTRITION_GOAL)
        return missing

    @staticmethod
    def _missing_sensitive(
        context: SensitiveProfileContext | None, storage_is_granted: bool
    ) -> list[OnboardingRequiredField]:
        required = [
            OnboardingRequiredField.MEDICAL_CONDITIONS,
            OnboardingRequiredField.SMOKING_HISTORY,
            OnboardingRequiredField.DRINKING_HISTORY,
            OnboardingRequiredField.BODY_BUILD,
            OnboardingRequiredField.MEDICAL_NEEDS,
        ]
        if not storage_is_granted or context is None:
            return required

        missing: list[OnboardingRequiredField] = []
        if not context.medical_conditions:
            missing.append(OnboardingRequiredField.MEDICAL_CONDITIONS)
        if context.smoking_status is None or context.smoking_method is None:
            missing.append(OnboardingRequiredField.SMOKING_HISTORY)
        if context.drinking_status is None or (
            context.drinking_status != "never"
            and any(
                value is None
                for value in (
                    context.drinking_frequency,
                    context.drinking_average_intake,
                    context.last_alcohol_consumption,
                    context.alcohol_type,
                )
            )
        ):
            missing.append(OnboardingRequiredField.DRINKING_HISTORY)
        if context.body_build is None:
            missing.append(OnboardingRequiredField.BODY_BUILD)
        # The stored controlled collection uses [] as an explicit "none selected" declaration.
        if context.medical_needs is None:
            missing.append(OnboardingRequiredField.MEDICAL_NEEDS)
        return missing
