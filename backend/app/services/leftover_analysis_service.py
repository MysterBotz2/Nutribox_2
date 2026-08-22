from decimal import Decimal

from app.models.leftover_analysis import LeftoverAnalysis
from app.models.meal import Meal
from app.repositories.leftover_analysis_repository import LeftoverAnalysisRepository
from app.schemas.meal import MealAnalysisStatus
from app.services.meal_analysis_service import MealAnalysisService


class DuplicateLeftoverAnalysisError(ValueError):
    pass


class LeftoverAnalysisConflictError(ValueError):
    pass


class LeftoverRecognitionError(ValueError):
    pass


class LeftoverAnalysisService:
    """Create immutable post-meal analysis snapshots without changing a meal."""

    _NUTRIENTS = (
        ("calories", "total_calories"),
        ("protein_g", "total_protein_g"),
        ("carbohydrates_g", "total_carbohydrates_g"),
        ("fat_g", "total_fat_g"),
        ("fiber_g", "total_fiber_g"),
    )

    def __init__(self, repository: LeftoverAnalysisRepository, meal_analysis_service: MealAnalysisService) -> None:
        self._repository = repository
        self._meal_analysis_service = meal_analysis_service

    def create(self, meal: Meal, leftover_weight_grams: Decimal, image_bytes: bytes | None = None, content_type: str | None = None) -> LeftoverAnalysis:
        if self._repository.get_by_meal_id(meal.id):
            raise DuplicateLeftoverAnalysisError("A leftover analysis already exists.")
        if leftover_weight_grams == 0:
            return self._persist(meal, leftover_weight_grams, {name: Decimal("0") for name, _ in self._NUTRIENTS}, "zero_leftover")
        if image_bytes is None or content_type is None:
            raise ValueError("A food image is required for non-zero leftovers.")
        result = self._meal_analysis_service.analyze(image_bytes=image_bytes, content_type=content_type, weight_grams=leftover_weight_grams)
        if result.status != MealAnalysisStatus.CALCULATED:
            raise LeftoverRecognitionError(result.status.value)
        return self._persist(meal, leftover_weight_grams, {name: getattr(result.nutrition, name) for name, _ in self._NUTRIENTS}, result.recognition_source, result.food.name)

    def _persist(self, meal: Meal, leftover_weight_grams: Decimal, leftovers: dict[str, Decimal], source: str, recognized_food_name: str | None = None) -> LeftoverAnalysis:
        consumed: dict[str, Decimal] = {}
        for nutrient, meal_field in self._NUTRIENTS:
            value = getattr(meal, meal_field) - leftovers[nutrient]
            if value < 0:
                raise LeftoverAnalysisConflictError("Leftover nutrition is inconsistent with the original meal snapshot.")
            consumed[nutrient] = value
        analysis = LeftoverAnalysis(
            meal_id=meal.id, leftover_weight_grams=leftover_weight_grams,
            leftover_calories=leftovers["calories"], leftover_protein_g=leftovers["protein_g"], leftover_carbohydrates_g=leftovers["carbohydrates_g"], leftover_fat_g=leftovers["fat_g"], leftover_fiber_g=leftovers["fiber_g"],
            consumed_calories=consumed["calories"], consumed_protein_g=consumed["protein_g"], consumed_carbohydrates_g=consumed["carbohydrates_g"], consumed_fat_g=consumed["fat_g"], consumed_fiber_g=consumed["fiber_g"], source=source, recognized_food_name=recognized_food_name,
        )
        self._repository.add(analysis)
        self._repository.session.flush()
        return analysis
