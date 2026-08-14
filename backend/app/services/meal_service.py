from decimal import Decimal, ROUND_HALF_UP

from app.models.meal import Meal, MealItem
from app.repositories.meal_repository import MealRepository
from app.schemas.meal import MealItemCreateRequest
from app.services.nutrient_calculator import PORTION_NUTRIENT_QUANTUM, NutrientCalculator
from app.services.nutrition_service import NutritionService


class MealFoodNotFoundError(ValueError):
    """Raised when a requested canonical food cannot be recorded."""


class MealService:
    """Transactional server-side creation and retrieval of meal snapshots."""

    def __init__(
        self,
        nutrition_service: NutritionService,
        meal_repository: MealRepository,
        nutrient_calculator: NutrientCalculator | None = None,
    ) -> None:
        self._nutrition_service = nutrition_service
        self._meal_repository = meal_repository
        self._nutrient_calculator = nutrient_calculator or NutrientCalculator()

    def create_meal(self, items: list[MealItemCreateRequest], user_id: int) -> Meal:
        session = self._meal_repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            meal_items: list[MealItem] = []
            for item_request in items:
                food = self._nutrition_service.get_food(item_request.food_id)
                if food is None:
                    raise MealFoodNotFoundError("Food record was not found.")
                nutrition = self._nutrient_calculator.calculate_extended(
                    self._nutrition_service.get_extended_nutrition_per_100g(food),
                    item_request.weight_grams,
                )
                meal_items.append(
                    MealItem(
                        food_id=food.id,
                        weight_grams=item_request.weight_grams,
                        calculated_calories=nutrition.calories,
                        calculated_protein_g=nutrition.protein_g,
                        calculated_carbohydrates_g=nutrition.carbohydrates_g,
                        calculated_fat_g=nutrition.fat_g,
                        calculated_fiber_g=nutrition.fiber_g,
                        calculated_saturated_fat_g=nutrition.saturated_fat_g,
                        calculated_sugars_g=nutrition.sugars_g,
                        calculated_sodium_mg=nutrition.sodium_mg,
                        calculated_cholesterol_mg=nutrition.cholesterol_mg,
                        calculated_omega_3_g=nutrition.omega_3_g,
                        calculated_omega_6_g=nutrition.omega_6_g,
                        calculated_calcium_mg=nutrition.calcium_mg,
                        calculated_potassium_mg=nutrition.potassium_mg,
                        calculated_zinc_mg=nutrition.zinc_mg,
                        calculated_iron_mg=nutrition.iron_mg,
                        calculated_magnesium_mg=nutrition.magnesium_mg,
                        calculated_vitamin_a_mcg_rae=nutrition.vitamin_a_mcg_rae,
                        calculated_vitamin_b12_mcg=nutrition.vitamin_b12_mcg,
                        calculated_vitamin_c_mg=nutrition.vitamin_c_mg,
                        calculated_vitamin_d_mcg=nutrition.vitamin_d_mcg,
                        calculated_folate_mcg_dfe=nutrition.folate_mcg_dfe,
                        food_name_snapshot=food.name,
                        food_normalized_name_snapshot=food.normalized_name,
                        nutrition_source_type=food.source_type,
                        nutrition_source_name_snapshot=food.source_name,
                        nutrition_source_reference_snapshot=food.source_reference,
                        nutrition_is_estimated=(
                            food.source_type == "AI_estimate"
                            if food.source_type is not None
                            else None
                        ),
                    )
                )
            meal = Meal(
                user_id=user_id,
                total_calories=self._total(item.calculated_calories for item in meal_items),
                total_protein_g=self._total(item.calculated_protein_g for item in meal_items),
                total_carbohydrates_g=self._total(item.calculated_carbohydrates_g for item in meal_items),
                total_fat_g=self._total(item.calculated_fat_g for item in meal_items),
                total_fiber_g=self._total(item.calculated_fiber_g for item in meal_items),
                items=meal_items,
            )
            self._meal_repository.add(meal)
            session.flush()
        return meal

    def get_meal(self, meal_id: int, user_id: int) -> Meal | None:
        return self._meal_repository.get_by_id_for_user(meal_id, user_id)

    def list_meals(self, user_id: int, limit: int, offset: int) -> list[Meal]:
        return self._meal_repository.list_for_user(user_id, limit, offset)

    @staticmethod
    def _total(values: object) -> Decimal:
        return sum(values, Decimal("0")).quantize(
            PORTION_NUTRIENT_QUANTUM, rounding=ROUND_HALF_UP
        )
