from app.models.nutrition_target import NutritionTarget
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.schemas.nutrition_target import NutritionTargetUpdateRequest


class NutritionTargetService:
    """Retrieval and full-replacement upsert of explicit nutrition targets."""

    def __init__(self, target_repository: NutritionTargetRepository) -> None:
        self._targets = target_repository

    def get_target(self, user_id: int) -> NutritionTarget | None:
        return self._targets.get_by_user_id(user_id)

    def replace_target(
        self, user_id: int, request: NutritionTargetUpdateRequest
    ) -> NutritionTarget:
        session = self._targets.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            target = self._targets.get_by_user_id(user_id)
            if target is None:
                target = NutritionTarget(user_id=user_id)
                self._targets.add(target)
            target.calories = request.calories
            target.protein_g = request.protein_g
            target.carbohydrates_g = request.carbohydrates_g
            target.fat_g = request.fat_g
            target.fiber_g = request.fiber_g
            target.source_type = request.source_type.value
            target.source_reference = request.source_reference
            target.notes = request.notes
            session.flush()
        return target
