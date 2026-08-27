from decimal import Decimal, ROUND_HALF_UP

from app.models.food import normalize_food_name
from app.models.meal import Meal, MealItem
from app.repositories.meal_repository import MealRepository
from app.schemas.meal import MealItemCreateRequest
from app.services.nutrient_calculator import PORTION_NUTRIENT_QUANTUM, NutrientCalculator
from app.services.nutrition_service import NutritionService
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.schemas.meal_analysis_session import MealAnalysisSessionState
from app.services.meal_analysis_session_service import (
    MealAnalysisSessionConsumedError,
    MealAnalysisSessionExpiredError,
    MealAnalysisSessionNotFoundError,
)


_STORED_OPTIONAL_NUTRIENTS = frozenset({
    "saturated_fat_g", "sugars_g", "sodium_mg", "cholesterol_mg", "omega_3_g",
    "omega_6_g", "calcium_mg", "potassium_mg", "zinc_mg", "iron_mg",
    "magnesium_mg", "phosphorus_mg", "vitamin_b6_mg", "niacin_mg",
    "vitamin_a_mcg_rae", "vitamin_b12_mcg", "vitamin_c_mg", "vitamin_d_mcg",
    "folate_mcg_dfe",
})


class MealFoodNotFoundError(ValueError):
    """Raised when a requested canonical food cannot be recorded."""


class MealAnalysisSessionNotCalculatedError(ValueError):
    """Raised when a continuation session is incomplete."""


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
                        calculated_phosphorus_mg=nutrition.phosphorus_mg,
                        calculated_vitamin_b6_mg=nutrition.vitamin_b6_mg,
                        calculated_niacin_mg=nutrition.niacin_mg,
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
                        weight_source="manual",
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

    def create_meal_from_analysis_session(self, analysis_session_id: int, user_id: int) -> Meal:
        """Atomically materialize only an owned, calculated, unused session."""
        session = self._meal_repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            repository = MealAnalysisSessionRepository(session)
            item = repository.get_for_user(analysis_session_id, user_id, lock=True)
            if item is None:
                raise MealAnalysisSessionNotFoundError("Meal analysis session was not found.")
            from datetime import datetime, timezone
            if item.consumed_at is not None:
                raise MealAnalysisSessionConsumedError("Meal analysis session was already consumed.")
            if datetime.now(timezone.utc) >= item.expires_at:
                raise MealAnalysisSessionExpiredError("Meal analysis session has expired.")
            if item.status != "calculated":
                raise MealAnalysisSessionNotCalculatedError("Meal analysis session is not ready to create a meal.")
            state = MealAnalysisSessionState.model_validate(item.state)
            meal_items: list[MealItem] = []
            for component in state.components:
                if component.nutrition is None:
                    raise MealAnalysisSessionNotCalculatedError("Meal analysis session is incomplete.")
                nutrient = component.nutrition
                composite = component.composite_provenance_snapshot
                if composite is not None:
                    if component.nutrition_source != "ai_recipe_estimate":
                        raise MealAnalysisSessionNotCalculatedError("Composite meal analysis provenance is invalid.")
                    if composite.dish_name != component.recognized_name or composite.dish_weight_grams != component.estimated_weight_grams:
                        raise MealAnalysisSessionNotCalculatedError("Composite meal analysis provenance does not match its component.")
                    food_id = None
                    food_name = component.recognized_name
                    normalized_name = normalize_food_name(component.recognized_name)
                    source_type = "ai_recipe_estimate"
                    source_name = "AI recipe composition estimate"
                    source_reference = None
                    is_estimated = True
                    provenance = composite.model_dump(mode="json")
                else:
                    if component.resolved_reference is None:
                        raise MealAnalysisSessionNotCalculatedError("Meal analysis session is incomplete.")
                    food = self._nutrition_service.get_food_by_reference(component.resolved_reference)
                    if food is None:
                        raise MealFoodNotFoundError("Food reference for meal analysis session was not found.")
                    food_id = food.id
                    food_name = food.name
                    normalized_name = food.normalized_name
                    source_type = food.source_type
                    source_name = food.source_name
                    source_reference = food.source_reference
                    is_estimated = food.source_type == "AI_estimate" if food.source_type else None
                    provenance = None
                meal_items.append(MealItem(
                    food_id=food_id, weight_grams=component.estimated_weight_grams,
                    calculated_calories=Decimal(nutrient["calories"]), calculated_protein_g=Decimal(nutrient["protein_g"]),
                    calculated_carbohydrates_g=Decimal(nutrient["carbohydrates_g"]), calculated_fat_g=Decimal(nutrient["fat_g"]), calculated_fiber_g=Decimal(nutrient["fiber_g"]),
                    food_name_snapshot=food_name, food_normalized_name_snapshot=normalized_name,
                    nutrition_source_type=source_type, nutrition_source_name_snapshot=source_name,
                    nutrition_source_reference_snapshot=source_reference,
                    nutrition_is_estimated=is_estimated,
                    composite_provenance_snapshot=provenance,
                    weight_source="ai_estimate",
                    **{
                        f"calculated_{name}": Decimal(nutrient[name]) if nutrient.get(name) is not None else None
                        for name in _STORED_OPTIONAL_NUTRIENTS
                    },
                ))
            meal = Meal(
                user_id=user_id, measured_weight_grams=state.measured_weight_grams,
                total_calories=self._total(item.calculated_calories for item in meal_items),
                total_protein_g=self._total(item.calculated_protein_g for item in meal_items),
                total_carbohydrates_g=self._total(item.calculated_carbohydrates_g for item in meal_items),
                total_fat_g=self._total(item.calculated_fat_g for item in meal_items),
                total_fiber_g=self._total(item.calculated_fiber_g for item in meal_items), items=meal_items,
            )
            self._meal_repository.add(meal)
            session.flush()
            from datetime import datetime, timezone
            item.consumed_at = datetime.now(timezone.utc)
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
