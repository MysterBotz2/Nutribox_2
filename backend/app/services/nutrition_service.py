from decimal import Decimal

from app.models.food import Food, normalize_food_name
from app.repositories.food_alias_repository import FoodAliasRepository
from app.repositories.food_repository import FoodRepository
from app.schemas.nutrition import NutritionPer100g, PortionNutrition
from app.services.nutrient_calculator import ExtendedNutritionPer100g, NutrientCalculator


class NutritionService:
    """Application-level lookup behavior for food nutrition reference data."""

    def __init__(
        self,
        food_repository: FoodRepository,
        nutrient_calculator: NutrientCalculator | None = None,
        food_alias_repository: FoodAliasRepository | None = None,
    ) -> None:
        self._food_repository = food_repository
        self._nutrient_calculator = nutrient_calculator or NutrientCalculator()
        self._food_alias_repository = food_alias_repository

    def get_food(self, food_id: int) -> Food | None:
        return self._food_repository.get_by_id(food_id)

    def get_food_by_reference(self, reference: str) -> Food | None:
        if reference.startswith("food:"):
            try:
                return self.get_food(int(reference.removeprefix("food:")))
            except ValueError:
                return None
        return self._food_repository.get_by_source_reference(reference)

    def get_food_by_recognized_name(self, recognized_name: str) -> Food | None:
        """Backward-compatible name for exact canonical then alias resolution."""
        return self.resolve_food_name(recognized_name)

    def resolve_food_name(self, food_name: str) -> Food | None:
        """Resolve an exact normalized canonical name, then an exact alias."""
        normalized_name = normalize_food_name(food_name)
        food = self._food_repository.get_by_normalized_name(normalized_name)
        if food is not None or self._food_alias_repository is None:
            return food
        return self._food_alias_repository.get_food_by_normalized_alias(normalized_name)

    @staticmethod
    def get_nutrition_per_100g(food: Food) -> NutritionPer100g:
        """Convert a food record into the stable five-nutrient API representation."""
        return NutritionPer100g(
            calories=food.calories_per_100g,
            protein_g=food.protein_g_per_100g,
            carbohydrates_g=food.carbohydrates_g_per_100g,
            fat_g=food.fat_g_per_100g,
            fiber_g=food.fiber_g_per_100g,
        )

    @staticmethod
    def get_extended_nutrition_per_100g(food: Food) -> ExtendedNutritionPer100g:
        """Convert a food record into the internal V2 calculator representation."""
        return ExtendedNutritionPer100g(
            calories=food.calories_per_100g,
            protein_g=food.protein_g_per_100g,
            carbohydrates_g=food.carbohydrates_g_per_100g,
            fat_g=food.fat_g_per_100g,
            fiber_g=food.fiber_g_per_100g,
            saturated_fat_g=food.saturated_fat_g_per_100g,
            sugars_g=food.sugars_g_per_100g,
            sodium_mg=food.sodium_mg_per_100g,
            cholesterol_mg=food.cholesterol_mg_per_100g,
            omega_3_g=food.omega_3_g_per_100g,
            omega_6_g=food.omega_6_g_per_100g,
            calcium_mg=food.calcium_mg_per_100g,
            potassium_mg=food.potassium_mg_per_100g,
            zinc_mg=food.zinc_mg_per_100g,
            iron_mg=food.iron_mg_per_100g,
            magnesium_mg=food.magnesium_mg_per_100g,
            vitamin_a_mcg_rae=food.vitamin_a_mcg_rae_per_100g,
            vitamin_b12_mcg=food.vitamin_b12_mcg_per_100g,
            vitamin_c_mg=food.vitamin_c_mg_per_100g,
            vitamin_d_mcg=food.vitamin_d_mcg_per_100g,
            folate_mcg_dfe=food.folate_mcg_dfe_per_100g,
            phosphorus_mg=food.phosphorus_mg_per_100g,
            vitamin_b6_mg=food.vitamin_b6_mg_per_100g,
            niacin_mg=food.niacin_mg_per_100g,
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

        return food, PortionNutrition.from_extended(self._nutrient_calculator.calculate_extended(
            self.get_extended_nutrition_per_100g(food), weight_grams
        ))
