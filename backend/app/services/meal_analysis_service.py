from decimal import Decimal

from app.schemas.ai import RecognizedFood
from app.schemas.meal import (
    CalculatedMealAnalysis,
    FoodNotRecognizedMealAnalysis,
    MealAnalysisResponse,
    MealAnalysisStatus,
    NutritionReferenceNotFoundMealAnalysis,
    RequiresFoodSelectionMealAnalysis,
)
from app.schemas.nutrition import CalculatedFood
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.nutrient_calculator import NutrientCalculator
from app.services.nutrition_service import NutritionService


class MealAnalysisService:
    """Transient orchestration of recognition, canonical lookup, and calculation."""

    def __init__(
        self,
        food_recognition_provider: FoodRecognitionProvider,
        nutrition_service: NutritionService,
        nutrient_calculator: NutrientCalculator | None = None,
    ) -> None:
        self._food_recognition_provider = food_recognition_provider
        self._nutrition_service = nutrition_service
        self._nutrient_calculator = nutrient_calculator or NutrientCalculator()

    def analyze(
        self, *, image_bytes: bytes, content_type: str, weight_grams: Decimal
    ) -> MealAnalysisResponse:
        """Analyze one image and supplied whole-portion weight without persistence."""
        recognition = self._food_recognition_provider.recognize_food(
            image_bytes=image_bytes,
            content_type=content_type,
        )
        recognized_foods = [RecognizedFood(name=name) for name in recognition.food_names]

        if not recognized_foods:
            return FoodNotRecognizedMealAnalysis(
                status=MealAnalysisStatus.FOOD_NOT_RECOGNIZED,
                recognized_foods=[],
                recognition_source=recognition.source,
            )
        if len(recognized_foods) > 1:
            return RequiresFoodSelectionMealAnalysis(
                status=MealAnalysisStatus.REQUIRES_FOOD_SELECTION,
                recognized_foods=recognized_foods,
                recognition_source=recognition.source,
            )

        food = self._nutrition_service.get_food_by_recognized_name(
            recognized_foods[0].name
        )
        if food is None:
            return NutritionReferenceNotFoundMealAnalysis(
                status=MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND,
                recognized_foods=recognized_foods,
                recognition_source=recognition.source,
            )

        nutrition = self._nutrient_calculator.calculate_extended(
            self._nutrition_service.get_extended_nutrition_per_100g(food), weight_grams
        )
        return CalculatedMealAnalysis(
            status=MealAnalysisStatus.CALCULATED,
            recognized_foods=recognized_foods,
            recognition_source=recognition.source,
            food=CalculatedFood(id=food.id, name=food.name),
            weight_grams=weight_grams,
            nutrition=nutrition.to_legacy_portion_nutrition(),
            weight_source="manual",
        )
