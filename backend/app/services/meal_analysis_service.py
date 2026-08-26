from decimal import Decimal
from dataclasses import dataclass, fields
from enum import Enum
import logging
from uuid import uuid4

from app.schemas.ai import RecognizedFood
from app.schemas.meal import (
    CalculatedMealAnalysis,
    FoodNotRecognizedMealAnalysis,
    MealAnalysisResponse,
    MealAnalysisStatus,
    NutritionReferenceNotFoundMealAnalysis,
    RequiresFoodSelectionMealAnalysis,
    RequiresIngredientVerificationMealAnalysis,
)
from app.schemas.nutrition import CalculatedFood, PortionNutrition
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.composite_dish_estimator import (
    CompositeDishEstimator,
    CompositeDishEstimatorError,
)
from app.services.nutrient_calculator import NutrientCalculator
from app.services.nutrition_service import NutritionService
from app.services.usda_food_reference_service import UsdaFoodReferenceService
from app.models.food import normalize_food_name
from app.models.user_recipe import UserRecipe, UserRecipeIngredient
from app.repositories.user_recipe_repository import UserRecipeRepository
from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    IngredientResolutionStatus,
    CompositeIngredientSnapshot,
    CompositeProvenanceSnapshot,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
    SuggestedIngredient,
    PersonalRecipeMatch,
    WeightSource,
)
from app.services.meal_analysis_session_service import MealAnalysisSessionService
from app.services.meal_composition_service import ComposedPortion, allocate_component_weights
from app.services.nutrient_calculator import ExtendedPortionNutrition


logger = logging.getLogger(__name__)


class _InternalIngredientResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NUTRITION_REFERENCE_NOT_FOUND = "nutrition_reference_not_found"


@dataclass(frozen=True)
class _InternalIngredientResolution:
    food: object | None
    status: _InternalIngredientResolutionStatus


@dataclass(frozen=True)
class ComposedMealAnalysis:
    """Internal owner-bound result for the later selection and persistence APIs."""

    status: MealAnalysisStatus
    recognition_source: str
    state: MealAnalysisSessionState
    nutrition: ExtendedPortionNutrition | None
    session_id: int


class PersonalRecipeNotFoundError(ValueError):
    """Raised when an owner-scoped recipe choice is absent."""


class PersonalRecipeReuseError(ValueError):
    """Raised when a stored personal recipe cannot safely be reused."""


class MealAnalysisService:
    """Transient orchestration of recognition, canonical lookup, and calculation."""

    def __init__(
        self,
        food_recognition_provider: FoodRecognitionProvider,
        nutrition_service: NutritionService,
        nutrient_calculator: NutrientCalculator | None = None,
        usda_food_reference_service: UsdaFoodReferenceService | None = None,
        composite_dish_estimator: CompositeDishEstimator | None = None,
        user_recipe_repository: UserRecipeRepository | None = None,
    ) -> None:
        self._food_recognition_provider = food_recognition_provider
        self._nutrition_service = nutrition_service
        self._nutrient_calculator = nutrient_calculator or NutrientCalculator()
        self._usda_food_reference_service = usda_food_reference_service
        self._composite_dish_estimator = composite_dish_estimator
        self._user_recipe_repository = user_recipe_repository

    # These are dish-form markers, not a cuisine-specific recipe catalogue.
    # When absent, an unresolved item remains unresolved rather than risking a
    # speculative decomposition of a simple food.
    _PREPARED_DISH_MARKERS = frozenset({
        "stew", "soup", "curry", "casserole", "sandwich", "pizza", "salad",
        "sinigang", "adobo", "caldereta", "tinola", "pinakbet", "laing",
        "pancit", "bicol", "express",
    })

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
        if food is None and self._usda_food_reference_service is not None:
            usda_resolution = self._usda_food_reference_service.resolve(recognized_foods[0].name)
            if usda_resolution.candidate_names:
                return RequiresFoodSelectionMealAnalysis(
                    status=MealAnalysisStatus.REQUIRES_FOOD_SELECTION,
                    # USDA descriptions are reference-candidate display data, not new
                    # recognition output.  Keep this legacy response field within its
                    # recognition-domain contract; authenticated session responses put
                    # candidate identity/display data in components[].candidates.
                    recognized_foods=recognized_foods,
                    recognition_source=recognition.source,
                )
            food = usda_resolution.food
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
            nutrition=PortionNutrition.from_extended(nutrition),
            weight_source="manual",
        )

    def analyze_composed(
        self,
        *,
        user_id: int,
        image_bytes: bytes,
        content_type: str,
        measured_weight_grams: Decimal,
        session_service: MealAnalysisSessionService,
    ) -> ComposedMealAnalysis | None:
        """Build an owner-bound continuation state without changing the legacy API."""
        recognition = self._food_recognition_provider.recognize_food(
            image_bytes=image_bytes, content_type=content_type
        )
        if not recognition.components:
            return None
        portions = allocate_component_weights(
            measured_weight_grams,
            [component.estimated_proportion for component in recognition.components],
        )
        components = [
            self._resolve_component(user_id, component.name, component.estimated_proportion, portion)
            for component, portion in zip(recognition.components, portions, strict=True)
        ]
        state = MealAnalysisSessionState(
            measured_weight_grams=measured_weight_grams,
            components=components,
        )
        if any(component.resolution_status == ComponentResolutionStatus.REQUIRES_FOOD_SELECTION for component in components):
            status = MealAnalysisStatus.REQUIRES_FOOD_SELECTION
            nutrition = None
        elif any(component.resolution_status == ComponentResolutionStatus.REQUIRES_RECIPE_CONFIRMATION for component in components):
            status = MealAnalysisStatus.REQUIRES_RECIPE_CONFIRMATION
            nutrition = None
        elif any(component.resolution_status == ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION for component in components):
            status = MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
            nutrition = None
        elif any(component.resolution_status == ComponentResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND for component in components):
            status = MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND
            nutrition = None
        else:
            status = MealAnalysisStatus.CALCULATED
            nutrition = self._aggregate_extended(
                [
                    ExtendedPortionNutrition(**{
                        name: Decimal(value) if value is not None else None
                        for name, value in component.nutrition.items()
                    })  # type: ignore[arg-type]
                    for component in components
                    if component.nutrition is not None
                ]
            )
        persisted = session_service.create_session(user_id, state, status.value)
        return ComposedMealAnalysis(
            status=status,
            recognition_source=recognition.source,
            state=state,
            nutrition=nutrition,
            session_id=persisted.id,
        )

    def _resolve_component(
        self, user_id: int, name: str, raw_proportion: Decimal, portion: ComposedPortion
    ) -> MealAnalysisSessionComponent:
        food = self._nutrition_service.get_food_by_recognized_name(name)
        candidates: list[dict[str, str]] = []
        if food is None and self._usda_food_reference_service is not None:
            usda_resolution = self._usda_food_reference_service.resolve(name)
            candidates = [
                {"candidate_id": str(uuid4()), "name": candidate.description, "source": "usda", "source_reference_id": str(candidate.fdc_id)}
                for candidate in usda_resolution.candidates
            ]
            if not candidates:
                candidates = [{"candidate_id": str(uuid4()), "name": candidate, "source": "usda", "source_reference_id": ""} for candidate in usda_resolution.candidate_names]
            food = usda_resolution.food
        if candidates:
            status = ComponentResolutionStatus.REQUIRES_FOOD_SELECTION
            nutrition = None
            reference = None
            source = None
        elif food is None:
            recipe_matches = self._personal_recipe_matches(user_id, name)
            if recipe_matches:
                return MealAnalysisSessionComponent(
                    recognized_name=name,
                    raw_estimated_proportion=raw_proportion,
                    normalized_proportion=portion.normalized_proportion,
                    estimated_weight_grams=portion.estimated_weight_grams,
                    weight_source=WeightSource.AI_ESTIMATE,
                    resolution_status=ComponentResolutionStatus.REQUIRES_RECIPE_CONFIRMATION,
                    recipe_matches=recipe_matches,
                )
            composite = self._resolve_composite_component(name, raw_proportion, portion)
            if composite is not None:
                return composite
            status = ComponentResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND
            nutrition = None
            reference = None
            source = None
        else:
            status = ComponentResolutionStatus.RESOLVED
            calculated = self._nutrient_calculator.calculate_extended(
                self._nutrition_service.get_extended_nutrition_per_100g(food),
                portion.estimated_weight_grams,
            )
            nutrition = {
                field.name: (str(value) if value is not None else None)
                for field in fields(calculated)
                for value in (getattr(calculated, field.name),)
            }
            reference = food.source_reference or f"food:{food.id}"
            source = food.source_type
        return MealAnalysisSessionComponent(
            recognized_name=name,
            raw_estimated_proportion=raw_proportion,
            normalized_proportion=portion.normalized_proportion,
            estimated_weight_grams=portion.estimated_weight_grams,
            weight_source=WeightSource.AI_ESTIMATE,
            resolution_status=status,
            candidates=candidates,
            resolved_reference=reference,
            nutrition_source=source,
            nutrition=nutrition,
        )

    def _personal_recipe_matches(self, user_id: int, recognized_name: str) -> list[PersonalRecipeMatch]:
        if self._user_recipe_repository is None or not self._is_composite_dish_eligible(recognized_name):
            return []
        return [
            PersonalRecipeMatch(recipe_id=recipe.id, name=recipe.name)
            for recipe in self._user_recipe_repository.find_by_normalized_name_for_user(
                user_id, normalize_food_name(recognized_name)
            )
        ]

    @classmethod
    def _is_composite_dish_eligible(cls, name: str) -> bool:
        tokens = set(name.casefold().replace("-", " ").split())
        return bool(tokens & cls._PREPARED_DISH_MARKERS)

    def _resolve_composite_component(
        self, name: str, raw_proportion: Decimal, portion: ComposedPortion
    ) -> MealAnalysisSessionComponent | None:
        """Resolve one prepared dish through non-recursive ingredient references."""
        eligible = self._is_composite_dish_eligible(name)
        if self._composite_dish_estimator is None or not eligible:
            logger.info(
                "composite_fallback eligibility=%s estimator_called=false fallback_outcome=unresolved "
                "reason=%s",
                eligible,
                "estimator_unconfigured" if self._composite_dish_estimator is None else "ineligible",
            )
            return None
        logger.info("composite_fallback eligibility=true estimator_called=true")
        try:
            estimate = self._composite_dish_estimator.estimate_composition(
                dish_name=name, dish_weight_grams=portion.estimated_weight_grams
            )
        except CompositeDishEstimatorError as error:
            logger.warning(
                "composite_fallback estimator_called=true estimator_outcome=%s fallback_outcome=unresolved "
                "provider_status_code=%d",
                "invalid_output" if "invalid response" in error.detail else "provider_error",
                error.status_code,
            )
            raise
        logger.info(
            "composite_fallback estimator_called=true estimator_outcome=success ingredient_count=%d",
            len(estimate.ingredients),
        )
        return MealAnalysisSessionComponent(
            recognized_name=name,
            raw_estimated_proportion=raw_proportion,
            normalized_proportion=portion.normalized_proportion,
            estimated_weight_grams=portion.estimated_weight_grams,
            weight_source=WeightSource.AI_ESTIMATE,
            resolution_status=ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION,
            suggested_ingredients=[
                SuggestedIngredient(
                    name=ingredient.name,
                    suggested_proportion=ingredient.estimated_proportion,
                )
                for ingredient in estimate.ingredients
            ],
        )
        internal_portions = allocate_component_weights(
            portion.estimated_weight_grams,
            [ingredient.estimated_proportion for ingredient in estimate.ingredients],
        )
        snapshots: list[CompositeIngredientSnapshot] = []
        nutrition_values: list[ExtendedPortionNutrition] = []
        internal_resolutions = [
            (ingredient, internal_portion, self._resolve_internal_ingredient(ingredient.name))
            for ingredient, internal_portion in zip(estimate.ingredients, internal_portions, strict=True)
        ]
        internal_resolved_count = sum(
            result.status == _InternalIngredientResolutionStatus.RESOLVED
            for _, _, result in internal_resolutions
        )
        internal_ambiguous_count = sum(
            result.status == _InternalIngredientResolutionStatus.AMBIGUOUS
            for _, _, result in internal_resolutions
        )
        internal_not_found_count = sum(
            result.status == _InternalIngredientResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND
            for _, _, result in internal_resolutions
        )
        if internal_ambiguous_count or internal_not_found_count:
            logger.info(
                "composite_fallback internal_resolved_count=%d internal_ambiguous_count=%d "
                "internal_not_found_count=%d fallback_outcome=unresolved",
                internal_resolved_count,
                internal_ambiguous_count,
                internal_not_found_count,
            )
            return None
        for ingredient, internal_portion, resolution in internal_resolutions:
            food = resolution.food
            assert food is not None
            calculated = self._nutrient_calculator.calculate_extended(
                self._nutrition_service.get_extended_nutrition_per_100g(food),
                internal_portion.estimated_weight_grams,
            )
            nutrition_values.append(calculated)
            snapshots.append(CompositeIngredientSnapshot(
                ingredient_name=ingredient.name,
                raw_estimated_proportion=ingredient.estimated_proportion,
                normalized_proportion=internal_portion.normalized_proportion,
                estimated_weight_grams=internal_portion.estimated_weight_grams,
                nutrition_source=food.source_type or "local_database",
                source_reference_id=food.source_reference or f"food:{food.id}",
                reference_name=food.name,
                nutrition={field.name: (str(value) if value is not None else None) for field in fields(calculated) for value in (getattr(calculated, field.name),)},
            ))
        aggregate = self._aggregate_extended(nutrition_values)
        provenance = CompositeProvenanceSnapshot(
            dish_name=name,
            dish_weight_grams=portion.estimated_weight_grams,
            ingredients=snapshots,
        )
        logger.info(
            "composite_fallback internal_resolved_count=%d internal_ambiguous_count=%d "
            "internal_not_found_count=%d fallback_outcome=resolved",
            internal_resolved_count,
            internal_ambiguous_count,
            internal_not_found_count,
        )
        return MealAnalysisSessionComponent(
            recognized_name=name,
            raw_estimated_proportion=raw_proportion,
            normalized_proportion=portion.normalized_proportion,
            estimated_weight_grams=portion.estimated_weight_grams,
            weight_source=WeightSource.AI_ESTIMATE,
            resolution_status=ComponentResolutionStatus.RESOLVED,
            nutrition_source="ai_recipe_estimate",
            nutrition={field.name: (str(value) if value is not None else None) for field in fields(aggregate) for value in (getattr(aggregate, field.name),)},
            composite_provenance_snapshot=provenance,
        )

    def _resolve_internal_ingredient(self, name: str) -> _InternalIngredientResolution:
        """One-level direct resolution; ambiguous candidates are deliberately unsafe."""
        food = self._nutrition_service.get_food_by_recognized_name(name)
        if food is not None:
            return _InternalIngredientResolution(food, _InternalIngredientResolutionStatus.RESOLVED)
        if self._usda_food_reference_service is None:
            return _InternalIngredientResolution(None, _InternalIngredientResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND)
        resolution = self._usda_food_reference_service.resolve(name)
        if resolution.candidates or resolution.candidate_names:
            return _InternalIngredientResolution(None, _InternalIngredientResolutionStatus.AMBIGUOUS)
        if resolution.food is None:
            return _InternalIngredientResolution(None, _InternalIngredientResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND)
        return _InternalIngredientResolution(resolution.food, _InternalIngredientResolutionStatus.RESOLVED)

    def use_personal_recipe(
        self, *, user_id: int, session_id: int, component_id: str, recipe_id: int,
        session_service: MealAnalysisSessionService,
    ) -> ComposedMealAnalysis:
        """Resolve a recipe-confirmation component from exact stored references only."""
        persisted = session_service.get_session_for_user(session_id, user_id, lock=True)
        state = MealAnalysisSessionState.model_validate(persisted.state)
        component = self._recipe_confirmation_component(state, component_id)
        recipe = self._selected_personal_recipe(user_id, component, recipe_id)
        portions, foods = self._validated_recipe_portions(recipe, component.estimated_weight_grams)
        snapshots: list[CompositeIngredientSnapshot] = []
        nutrition_values: list[ExtendedPortionNutrition] = []
        for ingredient, portion, food in zip(recipe.ingredients, portions, foods, strict=True):
            calculated = self._nutrient_calculator.calculate_extended(
                self._nutrition_service.get_extended_nutrition_per_100g(food),
                portion.estimated_weight_grams,
            )
            nutrition_values.append(calculated)
            snapshots.append(CompositeIngredientSnapshot(
                ingredient_name=ingredient.name_snapshot,
                raw_estimated_proportion=ingredient.normalized_proportion,
                normalized_proportion=portion.normalized_proportion,
                estimated_weight_grams=portion.estimated_weight_grams,
                nutrition_source=ingredient.nutrition_source_type,
                source_reference_id=ingredient.resolved_reference,
                reference_name=food.name,
                nutrition={field.name: (str(value) if value is not None else None) for field in fields(calculated) for value in (getattr(calculated, field.name),)},
                ingredient_source=ingredient.ingredient_source,
                weight_source=WeightSource(ingredient.weight_source),
            ))
        aggregate = self._aggregate_extended(nutrition_values)
        component.resolution_status = ComponentResolutionStatus.RESOLVED
        component.recipe_matches = []
        component.suggested_ingredients = []
        component.candidates = []
        component.nutrition_source = "ai_recipe_estimate"
        component.nutrition = {field.name: (str(value) if value is not None else None) for field in fields(aggregate) for value in (getattr(aggregate, field.name),)}
        component.composite_provenance_snapshot = CompositeProvenanceSnapshot(
            estimation_method="personal_recipe",
            composition_source="personal_recipe",
            recipe_id=recipe.id,
            recipe_name_snapshot=recipe.name,
            dish_name=component.recognized_name,
            dish_weight_grams=component.estimated_weight_grams,
            ingredients=snapshots,
        )
        return self._persist_recipe_continuation(state, session_id, user_id, session_service)

    def review_personal_recipe(
        self, *, user_id: int, session_id: int, component_id: str, recipe_id: int,
        session_service: MealAnalysisSessionService,
    ) -> ComposedMealAnalysis:
        """Load recipe-derived suggestions into the existing verification workflow."""
        persisted = session_service.get_session_for_user(session_id, user_id, lock=True)
        state = MealAnalysisSessionState.model_validate(persisted.state)
        component = self._recipe_confirmation_component(state, component_id)
        recipe = self._selected_personal_recipe(user_id, component, recipe_id)
        portions, foods = self._validated_recipe_portions(recipe, component.estimated_weight_grams)
        component.recipe_matches = []
        component.nutrition = None
        component.nutrition_source = None
        component.composite_provenance_snapshot = None
        component.resolution_status = ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION
        component.suggested_ingredients = [
            SuggestedIngredient(
                name=ingredient.name_snapshot,
                suggested_proportion=ingredient.normalized_proportion,
                ingredient_source=ingredient.ingredient_source,
                included=True,
                weight_grams=portion.estimated_weight_grams,
                weight_source=WeightSource(ingredient.weight_source),
                resolution_status=IngredientResolutionStatus.RESOLVED,
                resolved_reference=ingredient.resolved_reference,
                nutrition_source=ingredient.nutrition_source_type,
                food_id=food.id,
                recipe_derived=True,
            )
            for ingredient, portion, food in zip(recipe.ingredients, portions, foods, strict=True)
        ]
        return self._persist_recipe_continuation(state, session_id, user_id, session_service)

    def analyze_component_as_new(
        self, *, user_id: int, session_id: int, component_id: str,
        session_service: MealAnalysisSessionService,
    ) -> ComposedMealAnalysis:
        """Explicitly bypass one personal match and invoke the estimator once."""
        persisted = session_service.get_session_for_user(session_id, user_id, lock=True)
        state = MealAnalysisSessionState.model_validate(persisted.state)
        component = self._recipe_confirmation_component(state, component_id)
        portion = ComposedPortion(component.normalized_proportion, component.estimated_weight_grams)
        resolved = self._resolve_composite_component(
            component.recognized_name, component.raw_estimated_proportion, portion
        )
        if resolved is None:
            raise PersonalRecipeReuseError("A new composition analysis is unavailable for this dish.")
        component_index = state.components.index(component)
        state.components[component_index] = resolved
        return self._persist_recipe_continuation(state, session_id, user_id, session_service)

    def _recipe_confirmation_component(
        self, state: MealAnalysisSessionState, component_id: str
    ) -> MealAnalysisSessionComponent:
        component = next((item for item in state.components if str(item.component_id) == component_id), None)
        if component is None:
            raise PersonalRecipeReuseError("Meal analysis component was not found.")
        if component.resolution_status != ComponentResolutionStatus.REQUIRES_RECIPE_CONFIRMATION:
            raise PersonalRecipeReuseError("Meal analysis component is not awaiting recipe confirmation.")
        return component

    def _selected_personal_recipe(
        self, user_id: int, component: MealAnalysisSessionComponent, recipe_id: int
    ) -> UserRecipe:
        if not any(match.recipe_id == recipe_id for match in component.recipe_matches):
            raise PersonalRecipeNotFoundError("Personal recipe was not found.")
        if self._user_recipe_repository is None:
            raise PersonalRecipeNotFoundError("Personal recipe was not found.")
        recipe = self._user_recipe_repository.get_by_id_for_user(recipe_id, user_id)
        if recipe is None:
            raise PersonalRecipeNotFoundError("Personal recipe was not found.")
        return recipe

    def _validated_recipe_portions(
        self, recipe: UserRecipe, component_weight: Decimal,
    ) -> tuple[list[ComposedPortion], list[object]]:
        ingredients = list(recipe.ingredients)
        if not ingredients or not component_weight.is_finite() or component_weight <= 0:
            raise PersonalRecipeReuseError("Personal recipe is not valid for reuse.")
        proportions = [item.normalized_proportion for item in ingredients]
        if any(not value.is_finite() or value <= 0 or value > 1 for value in proportions) or sum(proportions, Decimal("0")) != Decimal("1"):
            raise PersonalRecipeReuseError("Personal recipe is not valid for reuse.")
        foods: list[object] = []
        for ingredient in ingredients:
            food = self._load_exact_recipe_reference(ingredient)
            if food is None:
                raise PersonalRecipeReuseError("A personal recipe reference is no longer available.")
            foods.append(food)
        return allocate_component_weights(component_weight, proportions), foods

    def _load_exact_recipe_reference(self, ingredient: UserRecipeIngredient):
        reference = ingredient.resolved_reference
        if not reference:
            return None
        if ingredient.nutrition_source_type == "USDA":
            if not reference.startswith("fdcId:"):
                return None
            if self._usda_food_reference_service is not None:
                try:
                    return self._usda_food_reference_service.load_by_fdc_id(int(reference.removeprefix("fdcId:")))
                except ValueError:
                    return None
        return self._nutrition_service.get_food_by_reference(reference)

    def _persist_recipe_continuation(
        self, state: MealAnalysisSessionState, session_id: int, user_id: int,
        session_service: MealAnalysisSessionService,
    ) -> ComposedMealAnalysis:
        statuses = [component.resolution_status for component in state.components]
        if ComponentResolutionStatus.REQUIRES_RECIPE_CONFIRMATION in statuses:
            status, nutrition = MealAnalysisStatus.REQUIRES_RECIPE_CONFIRMATION, None
        elif ComponentResolutionStatus.REQUIRES_FOOD_SELECTION in statuses:
            status, nutrition = MealAnalysisStatus.REQUIRES_FOOD_SELECTION, None
        elif ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION in statuses:
            status, nutrition = MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION, None
        elif ComponentResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND in statuses:
            status, nutrition = MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND, None
        else:
            status = MealAnalysisStatus.CALCULATED
            nutrition = self._aggregate_extended([
                ExtendedPortionNutrition(**{name: Decimal(value) if value is not None else None for name, value in component.nutrition.items()})
                for component in state.components if component.nutrition is not None
            ])
        session_service.update_session_state(session_id, user_id, state, status.value)
        return ComposedMealAnalysis(status=status, recognition_source="session", state=state, nutrition=nutrition, session_id=session_id)

    def apply_selection(
        self,
        *,
        user_id: int,
        session_id: int,
        component_id: str,
        candidate_id: str | None,
        candidate_name: str | None,
        session_service: MealAnalysisSessionService,
    ) -> ComposedMealAnalysis:
        """Resolve exactly one stored candidate without calling recognition again."""
        persisted = session_service.get_session_for_user(session_id, user_id, lock=True)
        state = MealAnalysisSessionState.model_validate(persisted.state)
        component = next((item for item in state.components if str(item.component_id) == component_id), None)
        if component is None:
            raise ValueError("Meal analysis component was not found.")
        if component.resolution_status != ComponentResolutionStatus.REQUIRES_FOOD_SELECTION:
            raise ValueError("Meal analysis component is not awaiting selection.")
        matches = [candidate for candidate in component.candidates if (candidate_id is not None and candidate.get("candidate_id") == candidate_id) or (candidate_id is None and candidate_name is not None and candidate["name"] == candidate_name)]
        if len(matches) != 1:
            raise ValueError("Selected nutrition reference is not valid or is ambiguous for this component.")
        candidate = matches[0]
        source = candidate.get("source")
        source_reference_id = candidate.get("source_reference_id")
        if source == "usda" and source_reference_id and self._usda_food_reference_service is not None:
            try:
                food = self._usda_food_reference_service.load_by_fdc_id(int(source_reference_id))
            except ValueError:
                food = None
        elif source == "local_database" and source_reference_id:
            try:
                food = self._nutrition_service.get_food(int(source_reference_id))
            except ValueError:
                food = None
        else:
            # Legacy short-lived session candidates did not retain a source ID.
            food = self._nutrition_service.get_food_by_recognized_name(candidate["name"])
        if food is None:
            raise ValueError("Selected nutrition reference is no longer available.")
        calculated = self._nutrient_calculator.calculate_extended(
            self._nutrition_service.get_extended_nutrition_per_100g(food), component.estimated_weight_grams
        )
        component.resolution_status = ComponentResolutionStatus.RESOLVED
        component.resolved_reference = food.source_reference or f"food:{food.id}"
        component.nutrition_source = food.source_type
        component.candidates = []
        component.nutrition = {field.name: (str(value) if value is not None else None) for field in fields(calculated) for value in (getattr(calculated, field.name),)}
        if any(item.resolution_status == ComponentResolutionStatus.REQUIRES_FOOD_SELECTION for item in state.components):
            status = MealAnalysisStatus.REQUIRES_FOOD_SELECTION
            nutrition = None
        elif any(item.resolution_status == ComponentResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND for item in state.components):
            status = MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND
            nutrition = None
        else:
            status = MealAnalysisStatus.CALCULATED
            nutrition = self._aggregate_extended([ExtendedPortionNutrition(**{name: Decimal(value) if value is not None else None for name, value in item.nutrition.items()}) for item in state.components if item.nutrition is not None])
        session_service.update_session_state(session_id, user_id, state, status.value)
        return ComposedMealAnalysis(status=status, recognition_source="session", state=state, nutrition=nutrition, session_id=session_id)

    def verify_ingredients(self, *, user_id: int, session_id: int, component_id: str, ingredients, session_service: MealAnalysisSessionService) -> ComposedMealAnalysis:
        """Resolve user-confirmed composition from owner-bound transient state only."""
        persisted = session_service.get_session_for_user(session_id, user_id, lock=True)
        state = MealAnalysisSessionState.model_validate(persisted.state)
        component = next((item for item in state.components if str(item.component_id) == component_id), None)
        if component is None or component.resolution_status != ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION:
            raise ValueError("Meal analysis component is not awaiting ingredient verification.")
        active = [item for item in ingredients if item.included]
        if not active:
            raise ValueError("Confirm at least one included ingredient.")
        supplied = [item.weight_grams is not None for item in active]
        if any(supplied) and not all(supplied):
            raise ValueError("Provide weights for every included ingredient or leave all weights blank.")
        existing = {str(item.ingredient_id): item for item in component.suggested_ingredients}
        confirmed = []
        for item in active:
            prior = existing.get(str(item.ingredient_id)) if item.ingredient_id else None
            confirmed.append(SuggestedIngredient(
                ingredient_id=prior.ingredient_id if prior else uuid4(), name=" ".join(item.name.split()),
                suggested_proportion=prior.suggested_proportion if prior else Decimal("1"), ingredient_source="user_confirmed",
                included=True, weight_grams=item.weight_grams,
                weight_source=WeightSource.USER_CONFIRMED if all(supplied) else WeightSource.AI_ESTIMATE,
                resolved_reference=prior.resolved_reference if prior and prior.name == " ".join(item.name.split()) else None,
                nutrition_source=prior.nutrition_source if prior and prior.name == " ".join(item.name.split()) else None,
                food_id=prior.food_id if prior and prior.name == " ".join(item.name.split()) else None,
                recipe_derived=prior.recipe_derived if prior else False,
            ))
        if all(supplied):
            if sum((item.weight_grams for item in confirmed if item.weight_grams is not None), Decimal("0")) != component.estimated_weight_grams:
                raise ValueError("Confirmed ingredient weights must equal the component weight exactly.")
            portions = None
        else:
            portions = allocate_component_weights(component.estimated_weight_grams, [item.suggested_proportion for item in confirmed])
        nutrition_values: list[ExtendedPortionNutrition] = []
        snapshots: list[CompositeIngredientSnapshot] = []
        unresolved = False
        for index, item in enumerate(confirmed):
            weight = item.weight_grams if portions is None else portions[index].estimated_weight_grams
            item.weight_grams = weight
            food = self._nutrition_service.get_food(item.food_id) if item.food_id is not None else self._nutrition_service.get_food_by_recognized_name(item.name)
            candidates: list[dict[str, str]] = []
            if food is None and self._usda_food_reference_service is not None:
                resolved = self._usda_food_reference_service.resolve(item.name)
                food = resolved.food
                candidates = [{"candidate_id": str(uuid4()), "name": candidate.description, "source": "usda", "source_reference_id": str(candidate.fdc_id)} for candidate in resolved.candidates]
            if food is None:
                unresolved = True
                item.resolution_status = IngredientResolutionStatus.REQUIRES_FOOD_SELECTION if candidates else IngredientResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND
                item.candidates = candidates
                continue
            item.resolution_status = IngredientResolutionStatus.RESOLVED
            item.resolved_reference = food.source_reference or f"food:{food.id}"
            item.nutrition_source = food.source_type
            item.food_id = food.id
            calculated = self._nutrient_calculator.calculate_extended(self._nutrition_service.get_extended_nutrition_per_100g(food), weight)
            item.nutrition = {field.name: (str(value) if value is not None else None) for field in fields(calculated) for value in (getattr(calculated, field.name),)}
            nutrition_values.append(calculated)
            snapshots.append(CompositeIngredientSnapshot(ingredient_name=item.name, raw_estimated_proportion=item.suggested_proportion, normalized_proportion=(weight / component.estimated_weight_grams), estimated_weight_grams=weight, nutrition_source=food.source_type or "local_database", source_reference_id=item.resolved_reference, reference_name=food.name, nutrition=item.nutrition, ingredient_source="user_confirmed", weight_source=item.weight_source))
        component.suggested_ingredients = confirmed
        if unresolved:
            session_service.update_session_state(session_id, user_id, state, MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION.value)
            return ComposedMealAnalysis(status=MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION, recognition_source="session", state=state, nutrition=None, session_id=session_id)
        self._reevaluate_composite_component(component)
        status = MealAnalysisStatus.CALCULATED if all(item.resolution_status == ComponentResolutionStatus.RESOLVED for item in state.components) else MealAnalysisStatus.NUTRITION_REFERENCE_NOT_FOUND
        nutrition = self._aggregate_extended([ExtendedPortionNutrition(**{name: Decimal(value) if value is not None else None for name, value in item.nutrition.items()}) for item in state.components if item.nutrition is not None]) if status == MealAnalysisStatus.CALCULATED else None
        session_service.update_session_state(session_id, user_id, state, status.value)
        return ComposedMealAnalysis(status=status, recognition_source="session", state=state, nutrition=nutrition, session_id=session_id)

    def apply_ingredient_selection(self, *, user_id: int, session_id: int, component_id: str, ingredient_id: str, candidate_id: str, session_service: MealAnalysisSessionService) -> ComposedMealAnalysis:
        persisted = session_service.get_session_for_user(session_id, user_id, lock=True)
        state = MealAnalysisSessionState.model_validate(persisted.state)
        component = next((item for item in state.components if str(item.component_id) == component_id), None)
        if component is None or component.resolution_status != ComponentResolutionStatus.REQUIRES_INGREDIENT_VERIFICATION:
            raise ValueError("Meal analysis component is not awaiting ingredient verification.")
        ingredient = next((item for item in component.suggested_ingredients if str(item.ingredient_id) == ingredient_id), None)
        if ingredient is None or ingredient.resolution_status != IngredientResolutionStatus.REQUIRES_FOOD_SELECTION:
            raise ValueError("Ingredient is not awaiting nutrition reference selection.")
        candidate = next((item for item in ingredient.candidates if item.get("candidate_id") == candidate_id), None)
        if candidate is None:
            raise ValueError("Selected nutrition reference is not valid for this ingredient.")
        food = None
        if candidate.get("source") == "usda" and candidate.get("source_reference_id") and self._usda_food_reference_service is not None:
            try:
                food = self._usda_food_reference_service.load_by_fdc_id(int(candidate["source_reference_id"]))
            except ValueError:
                food = None
        if food is None:
            raise ValueError("Selected nutrition reference is no longer available.")
        ingredient.resolution_status = IngredientResolutionStatus.RESOLVED
        ingredient.candidates = []
        ingredient.resolved_reference = food.source_reference or f"food:{food.id}"
        ingredient.nutrition_source = food.source_type
        ingredient.food_id = food.id
        self._reevaluate_composite_component(component)
        status = MealAnalysisStatus.CALCULATED if component.resolution_status == ComponentResolutionStatus.RESOLVED else MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION
        nutrition = ExtendedPortionNutrition(**{name: Decimal(value) if value is not None else None for name, value in component.nutrition.items()}) if component.nutrition is not None else None
        session_service.update_session_state(session_id, user_id, state, status.value)
        return ComposedMealAnalysis(status=status, recognition_source="session", state=state, nutrition=nutrition, session_id=session_id)

    def _reevaluate_composite_component(self, component: MealAnalysisSessionComponent) -> None:
        ingredients = [item for item in component.suggested_ingredients if item.included]
        if any(item.resolution_status == IngredientResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND for item in ingredients):
            component.resolution_status = ComponentResolutionStatus.NUTRITION_REFERENCE_NOT_FOUND; return
        if any(item.resolution_status == IngredientResolutionStatus.REQUIRES_FOOD_SELECTION for item in ingredients):
            component.resolution_status = ComponentResolutionStatus.REQUIRES_FOOD_SELECTION; return
        if not ingredients or any(item.food_id is None or item.weight_grams is None for item in ingredients):
            raise ValueError("Confirmed ingredients require resolved references and reconciled weights.")
        if sum((item.weight_grams for item in ingredients if item.weight_grams is not None), Decimal("0")) != component.estimated_weight_grams:
            raise ValueError("Confirmed ingredient weights must equal the component weight exactly.")
        values: list[ExtendedPortionNutrition] = []; snapshots: list[CompositeIngredientSnapshot] = []
        for item in ingredients:
            food = self._nutrition_service.get_food(item.food_id)
            if food is None: raise ValueError("Confirmed nutrition reference is no longer available.")
            calculated = self._nutrient_calculator.calculate_extended(self._nutrition_service.get_extended_nutrition_per_100g(food), item.weight_grams)
            item.nutrition = {field.name: (str(value) if value is not None else None) for field in fields(calculated) for value in (getattr(calculated, field.name),)}
            values.append(calculated)
            snapshots.append(CompositeIngredientSnapshot(ingredient_name=item.name, raw_estimated_proportion=item.suggested_proportion, normalized_proportion=item.weight_grams / component.estimated_weight_grams, estimated_weight_grams=item.weight_grams, nutrition_source=food.source_type or "local_database", source_reference_id=item.resolved_reference or f"food:{food.id}", reference_name=food.name, nutrition=item.nutrition, ingredient_source="user_confirmed", weight_source=item.weight_source))
        aggregate = self._aggregate_extended(values)
        component.resolution_status = ComponentResolutionStatus.RESOLVED; component.candidates = []; component.nutrition_source = "ai_recipe_estimate"
        component.nutrition = {field.name: (str(value) if value is not None else None) for field in fields(aggregate) for value in (getattr(aggregate, field.name),)}
        component.composite_provenance_snapshot = CompositeProvenanceSnapshot(dish_name=component.recognized_name, dish_weight_grams=component.estimated_weight_grams, ingredients=snapshots, composition_source="user_confirmed")

    @staticmethod
    def _aggregate_extended(values: list[ExtendedPortionNutrition]) -> ExtendedPortionNutrition:
        if not values:
            raise ValueError("At least one resolved component is required.")
        result: dict[str, Decimal | None] = {}
        for field in fields(ExtendedPortionNutrition):
            field_values = [getattr(value, field.name) for value in values]
            result[field.name] = (
                sum(field_values, Decimal("0"))
                if all(value is not None for value in field_values)
                else None
            )
        return ExtendedPortionNutrition(**result)  # type: ignore[arg-type]
