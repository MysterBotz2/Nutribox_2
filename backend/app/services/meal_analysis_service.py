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
from app.schemas.meal_analysis_session import (
    ComponentResolutionStatus,
    CompositeIngredientSnapshot,
    CompositeProvenanceSnapshot,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
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


class MealAnalysisService:
    """Transient orchestration of recognition, canonical lookup, and calculation."""

    def __init__(
        self,
        food_recognition_provider: FoodRecognitionProvider,
        nutrition_service: NutritionService,
        nutrient_calculator: NutrientCalculator | None = None,
        usda_food_reference_service: UsdaFoodReferenceService | None = None,
        composite_dish_estimator: CompositeDishEstimator | None = None,
    ) -> None:
        self._food_recognition_provider = food_recognition_provider
        self._nutrition_service = nutrition_service
        self._nutrient_calculator = nutrient_calculator or NutrientCalculator()
        self._usda_food_reference_service = usda_food_reference_service
        self._composite_dish_estimator = composite_dish_estimator

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
                    recognized_foods=[RecognizedFood(name=name) for name in usda_resolution.candidate_names],
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
            self._resolve_component(component.name, component.estimated_proportion, portion)
            for component, portion in zip(recognition.components, portions, strict=True)
        ]
        state = MealAnalysisSessionState(
            measured_weight_grams=measured_weight_grams,
            components=components,
        )
        if any(component.resolution_status == ComponentResolutionStatus.REQUIRES_FOOD_SELECTION for component in components):
            status = MealAnalysisStatus.REQUIRES_FOOD_SELECTION
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
        self, name: str, raw_proportion: Decimal, portion: ComposedPortion
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
