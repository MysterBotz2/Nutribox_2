from app.models.nutrition_profile import NutritionProfile
from app.repositories.nutrition_profile_repository import NutritionProfileRepository
from app.schemas.profile import NutritionProfileUpdateRequest


class NutritionProfileService:
    """Profile retrieval and full-replacement upsert operations."""

    def __init__(self, profile_repository: NutritionProfileRepository) -> None:
        self._profiles = profile_repository

    def get_profile(self, user_id: int) -> NutritionProfile | None:
        return self._profiles.get_by_user_id(user_id)

    def replace_profile(
        self, user_id: int, request: NutritionProfileUpdateRequest
    ) -> NutritionProfile:
        session = self._profiles.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            profile = self._profiles.get_by_user_id(user_id)
            if profile is None:
                profile = NutritionProfile(user_id=user_id)
                self._profiles.add(profile)
            profile.age = request.age
            profile.height_cm = request.height_cm
            profile.weight_kg = request.weight_kg
            profile.activity_level = (
                request.activity_level.value if request.activity_level is not None else None
            )
            profile.nutrition_goal = request.nutrition_goal.value if request.nutrition_goal else None
            profile.dietary_restrictions = request.dietary_restrictions
            profile.allergies = request.allergies
            profile.budget_allotment = (
                request.budget_allotment.value if request.budget_allotment is not None else None
            )
            session.flush()
        return profile
