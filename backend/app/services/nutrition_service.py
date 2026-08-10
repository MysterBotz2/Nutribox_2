from decimal import Decimal

from app.models.food import Food, normalize_food_name
from app.repositories.food_repository import FoodRepository
from app.schemas.nutrition import NutritionPer100g, PortionNutrition
from app.services.nutrient_calculator import NutrientCalculator


class NutritionService:
    """Application-level lookup behavior for food nutrition reference data."""

    def __init__(
        self,
        food_repository: FoodRepository,
        nutrient_calculator: NutrientCalculator | None = None,
    ) -> None:
        self._food_repository = food_repository
        self._nutrient_calculator = nutrient_calculator or NutrientCalculator()

    def get_food(self, food_id: int) -> Food | None:
        return self._food_repository.get_by_id(food_id)

    def get_food_by_recognized_name(self, recognized_name: str) -> Food | None:
        """Find an exact canonical food match using deterministic normalization."""
        return self._food_repository.get_by_normalized_name(
            normalize_food_name(recognized_name)
        )

    @staticmethod
    def get_nutrition_per_100g(food: Food) -> NutritionPer100g:
        """Convert a canonical food record into calculator input values."""
        return NutritionPer100g(
            calories=food.calories_per_100g,
            protein_g=food.protein_g_per_100g,
            carbohydrates_g=food.carbohydrates_g_per_100g,
            fat_g=food.fat_g_per_100g,
            fiber_g=food.fiber_g_per_100g,
        )

    def search_foods(self, query: str) -> list[Food]:
        if not query.strip():
            return []
        return self._food_repository.search(normalize_food_name(query))

    def calculate_portion(
        self, food_id: int, weight_grams: Decimal
    ) -> tuple[Food, PortionNutrition] | None:
        """Look up reference nutrients and calculate a measured portion."""
        food = self.get_food(food_id)
        if food is None:
            return None

        nutrition_per_100g = self.get_nutrition_per_100g(food)
        return food, self._nutrient_calculator.calculate(
            nutrition_per_100g, weight_grams
        )
