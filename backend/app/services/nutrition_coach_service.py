from datetime import datetime, timezone

from app.models.nutrition_profile import NutritionProfile
from app.repositories.nutrition_profile_repository import NutritionProfileRepository
from app.schemas.nutrition_coach import NutritionCoachResponse
from app.schemas.nutrition_target import TargetNutrientValues, TargetSourceType
from app.services.nutrition_coach_provider import (
    NutritionCoachContext,
    NutritionCoachProfileContext,
    NutritionCoachProvider,
    NutritionCoachTargetContext,
)
from app.services.nutrition_target_comparison_service import NutritionTargetComparisonService
from app.services.nutrition_target_service import NutritionTargetService
from app.services.progress_service import ProgressService


class NutritionCoachService:
    """Assemble trusted nutrition context and delegate only prepared data to a coach provider."""

    def __init__(
        self,
        provider: NutritionCoachProvider,
        profile_repository: NutritionProfileRepository,
        target_service: NutritionTargetService,
        progress_service: ProgressService,
        target_comparison_service: NutritionTargetComparisonService,
    ) -> None:
        self._provider = provider
        self._profiles = profile_repository
        self._targets = target_service
        self._progress = progress_service
        self._comparison = target_comparison_service

    async def generate_guidance(
        self, user_id: int, timezone_name: str, question: str | None
    ) -> NutritionCoachResponse:
        profile = self._profiles.get_by_user_id(user_id)
        today = self._progress.today(user_id, timezone_name)
        comparison = self._comparison.status_for_today_progress(user_id, today)
        target = self._targets.get_target(user_id)
        weekly = self._progress.summary(user_id, days=7, timezone_name=timezone_name)
        result = await self._provider.generate_guidance(
            NutritionCoachContext(
                timezone=timezone_name,
                profile=self._profile_context(profile),
                target=(
                    NutritionCoachTargetContext(
                        values=TargetNutrientValues(
                            calories=target.calories,
                            protein_g=target.protein_g,
                            carbohydrates_g=target.carbohydrates_g,
                            fat_g=target.fat_g,
                            fiber_g=target.fiber_g,
                        ),
                        source_type=TargetSourceType(target.source_type),
                    )
                    if target is not None
                    else None
                ),
                today=today,
                target_comparison=comparison,
                weekly=weekly,
                question=question,
            )
        )
        return NutritionCoachResponse(
            message=result.message,
            highlights=list(result.highlights),
            provider=result.provider,
            generated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _profile_context(profile: NutritionProfile | None) -> NutritionCoachProfileContext | None:
        if profile is None:
            return None
        return NutritionCoachProfileContext(
            activity_level=profile.activity_level,
            nutrition_goal=profile.nutrition_goal,
            dietary_restrictions=tuple(profile.dietary_restrictions or ()),
            allergies=tuple(profile.allergies or ()),
        )
