from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.meal_operation_auth import (
    MealOperationPrincipal,
    get_optional_meal_operation_principal,
    require_meal_operation_principal,
)
from app.models.user import User
from app.repositories.food_repository import FoodRepository
from app.repositories.meal_repository import MealRepository
from app.repositories.user_recipe_repository import UserRecipeRepository
from app.routers.nutrition import get_nutrition_service
from app.schemas.meal import (
    CalculatedMealAnalysis,
    MealAnalysisCandidateResponse,
    MealAnalysisComponentResponse,
    MealAnalysisSelectionRequest,
    IngredientVerificationRequest,
    IngredientCandidateSelectionRequest,
    MealAnalysisStatus,
    NutritionReferenceNotFoundMealAnalysis,
    RequiresFoodSelectionMealAnalysis,
    RequiresIngredientVerificationMealAnalysis,
    RequiresRecipeConfirmationMealAnalysis,
    PersonalRecipeSelectionRequest,
    MealAnalysisResponse,
    MealCreateRequest,
    MealItemResponse,
    MealItemNutritionSource,
    MealListItem,
    MealListItemResponse,
    MealListResponse,
    MealResponse,
    MealTotals,
)
from app.schemas.ai import RecognizedFood
from app.schemas.nutrition import AdditionalNutrientValues, CalculatedFood, NutrientValues, PortionNutrition
from app.services.food_recognition_provider import FoodRecognitionProvider, FoodRecognitionProviderError
from app.services.food_recognition_selector import get_food_recognition_provider
from app.services.composite_dish_estimator import CompositeDishEstimator, CompositeDishEstimatorError
from app.services.composite_dish_estimator_selector import get_composite_dish_estimator
from app.services.image_validation import read_validated_image
from app.services.meal_analysis_service import (
    MealAnalysisService,
    PersonalRecipeNotFoundError,
    PersonalRecipeReuseError,
)
from app.services.meal_service import MealFoodNotFoundError, MealService
from app.services.nutrient_calculator import derive_energy_kj
from app.services.meal_service import MealAnalysisSessionNotCalculatedError
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.services.meal_analysis_session_service import MealAnalysisSessionConsumedError, MealAnalysisSessionExpiredError, MealAnalysisSessionNotFoundError, MealAnalysisSessionService
from app.services.nutrition_service import NutritionService
from app.services.usda_food_data_client import UsdaFoodDataClient
from app.services.usda_food_reference_service import UsdaFoodReferenceService
from app.core.config import settings
from app.repositories.leftover_analysis_repository import LeftoverAnalysisRepository
from app.schemas.leftover_analysis import LeftoverAnalysisProvenance, LeftoverAnalysisResponse, LeftoverNutrition
from app.services.leftover_analysis_service import DuplicateLeftoverAnalysisError, LeftoverAnalysisConflictError, LeftoverAnalysisService, LeftoverRecognitionError
from app.dependencies.user_recipes import get_user_recipe_service
from app.schemas.user_recipe import (
    SaveUserRecipeRequest,
    UserRecipeResponse,
    user_recipe_response_from_model,
)
from app.services.user_recipe_service import UserRecipeSaveEligibilityError, UserRecipeService

router = APIRouter(prefix="/api/meals", tags=["meals"])


def get_meal_analysis_service(
    provider: Annotated[FoodRecognitionProvider, Depends(get_food_recognition_provider)],
    composite_dish_estimator: Annotated[CompositeDishEstimator, Depends(get_composite_dish_estimator)],
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
    database_session: Annotated[Session, Depends(get_db)],
) -> MealAnalysisService:
    client = None
    if settings.usda_fdc_enabled and settings.usda_fdc_api_key:
        client = UsdaFoodDataClient(
            api_key=settings.usda_fdc_api_key,
            base_url=settings.usda_fdc_base_url,
            timeout_seconds=settings.usda_fdc_timeout_seconds,
        )
    return MealAnalysisService(
        provider,
        nutrition_service,
        usda_food_reference_service=UsdaFoodReferenceService(
            FoodRepository(database_session), client
        ),
        composite_dish_estimator=composite_dish_estimator,
        user_recipe_repository=UserRecipeRepository(database_session),
    )


def get_meal_service(database_session: Annotated[Session, Depends(get_db)]) -> MealService:
    return MealService(
        NutritionService(FoodRepository(database_session)),
        MealRepository(database_session),
    )


def get_meal_analysis_session_service(database_session: Annotated[Session, Depends(get_db)]) -> MealAnalysisSessionService:
    return MealAnalysisSessionService(MealAnalysisSessionRepository(database_session))


@router.post(
    "/analysis-sessions/{analysis_session_id}/components/{component_id}/save-recipe",
    response_model=UserRecipeResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_analysis_component_as_recipe(
    analysis_session_id: int,
    component_id: str,
    request: SaveUserRecipeRequest | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    recipe_service: Annotated[UserRecipeService, Depends(get_user_recipe_service)] = None,
) -> UserRecipeResponse:
    """Save a verified composite before its analysis session is consumed by meal logging."""
    try:
        recipe = recipe_service.save_from_analysis_component(
            user_id=current_user.id,
            analysis_session_id=analysis_session_id,
            component_id=component_id,
            recipe_name_override=request.name if request is not None else None,
        )
    except MealAnalysisSessionNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal analysis session was not found.") from None
    except MealAnalysisSessionExpiredError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Meal analysis session has expired.") from None
    except MealAnalysisSessionConsumedError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Meal analysis session was already consumed.") from None
    except UserRecipeSaveEligibilityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis component is not eligible to save as a personal recipe.",
        ) from None
    return user_recipe_response_from_model(recipe)


def _recipe_reuse_response(result, session_service, session_id: int, user_id: int):
    persisted = session_service.get_session_for_user(session_id, user_id)
    return composed_analysis_response(result, persisted.expires_at)


def _raise_recipe_reuse_http_error(error: Exception) -> None:
    if isinstance(error, MealAnalysisSessionNotFoundError | PersonalRecipeNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal recipe or analysis session was not found.") from None
    if isinstance(error, MealAnalysisSessionExpiredError):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Meal analysis session has expired.") from None
    if isinstance(error, MealAnalysisSessionConsumedError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Meal analysis session was already consumed.") from None
    if isinstance(error, PersonalRecipeReuseError | ValueError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Personal recipe reuse is not available for this analysis component.") from None
    raise error


@router.post("/analysis-sessions/{analysis_session_id}/components/{component_id}/use-recipe", response_model=MealAnalysisResponse)
def use_personal_recipe(
    analysis_session_id: int,
    component_id: str,
    selection: PersonalRecipeSelectionRequest,
    principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)],
    meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)],
) -> MealAnalysisResponse:
    try:
        result = meal_analysis_service.use_personal_recipe(
            user_id=principal.user_id, session_id=analysis_session_id, component_id=component_id,
            recipe_id=selection.recipe_id, session_service=session_service,
        )
        return _recipe_reuse_response(result, session_service, analysis_session_id, principal.user_id)
    except (MealAnalysisSessionNotFoundError, MealAnalysisSessionExpiredError, MealAnalysisSessionConsumedError, PersonalRecipeNotFoundError, PersonalRecipeReuseError, ValueError) as error:
        _raise_recipe_reuse_http_error(error)


@router.post("/analysis-sessions/{analysis_session_id}/components/{component_id}/review-recipe", response_model=MealAnalysisResponse)
def review_personal_recipe(
    analysis_session_id: int,
    component_id: str,
    selection: PersonalRecipeSelectionRequest,
    principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)],
    meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)],
) -> MealAnalysisResponse:
    try:
        result = meal_analysis_service.review_personal_recipe(
            user_id=principal.user_id, session_id=analysis_session_id, component_id=component_id,
            recipe_id=selection.recipe_id, session_service=session_service,
        )
        return _recipe_reuse_response(result, session_service, analysis_session_id, principal.user_id)
    except (MealAnalysisSessionNotFoundError, MealAnalysisSessionExpiredError, MealAnalysisSessionConsumedError, PersonalRecipeNotFoundError, PersonalRecipeReuseError, ValueError) as error:
        _raise_recipe_reuse_http_error(error)


@router.post("/analysis-sessions/{analysis_session_id}/components/{component_id}/analyze-as-new", response_model=MealAnalysisResponse)
def analyze_component_as_new(
    analysis_session_id: int,
    component_id: str,
    principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)],
    meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)],
) -> MealAnalysisResponse:
    try:
        result = meal_analysis_service.analyze_component_as_new(
            user_id=principal.user_id, session_id=analysis_session_id, component_id=component_id,
            session_service=session_service,
        )
        return _recipe_reuse_response(result, session_service, analysis_session_id, principal.user_id)
    except CompositeDishEstimatorError as error:
        detail = "Composite dish estimation service is temporarily unavailable. Please try again later."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if error.status_code == status.HTTP_429_TOO_MANY_REQUESTS else error.status_code, detail=detail if error.status_code == status.HTTP_429_TOO_MANY_REQUESTS else error.detail) from None
    except (MealAnalysisSessionNotFoundError, MealAnalysisSessionExpiredError, MealAnalysisSessionConsumedError, PersonalRecipeReuseError, ValueError) as error:
        _raise_recipe_reuse_http_error(error)


def _component_response(component) -> MealAnalysisComponentResponse:
    return MealAnalysisComponentResponse(
        component_id=component.component_id, recognized_name=component.recognized_name,
        raw_estimated_proportion=component.raw_estimated_proportion, normalized_proportion=component.normalized_proportion,
        estimated_weight_grams=component.estimated_weight_grams, weight_source=component.weight_source.value,
        resolution_status=component.resolution_status.value, nutrition_source=component.nutrition_source, resolved_reference=component.resolved_reference,
        candidates=[MealAnalysisCandidateResponse(**candidate) for candidate in component.candidates],
        nutrition=PortionNutrition(**component.nutrition) if component.nutrition is not None else None,
        composite_estimation=component.composite_provenance_snapshot is not None,
        suggested_ingredients=component.suggested_ingredients,
        recipe_matches=component.recipe_matches,
    )


def composed_analysis_response(result, expires_at):
    common = dict(
        recognized_foods=[RecognizedFood(name=component.recognized_name) for component in result.state.components],
        recognition_source=result.recognition_source, analysis_session_id=result.session_id,
        analysis_session_expires_at=expires_at, measured_weight_grams=result.state.measured_weight_grams,
        components=[_component_response(component) for component in result.state.components],
    )
    if result.status == MealAnalysisStatus.CALCULATED:
        return CalculatedMealAnalysis(**common, status=result.status, weight_grams=result.state.measured_weight_grams,
            nutrition=PortionNutrition.from_extended(result.nutrition), weight_source="ai_estimate")
    if result.status == MealAnalysisStatus.REQUIRES_FOOD_SELECTION:
        return RequiresFoodSelectionMealAnalysis(**common, status=result.status)
    if result.status == MealAnalysisStatus.REQUIRES_INGREDIENT_VERIFICATION:
        return RequiresIngredientVerificationMealAnalysis(**common, status=result.status)
    if result.status == MealAnalysisStatus.REQUIRES_RECIPE_CONFIRMATION:
        return RequiresRecipeConfirmationMealAnalysis(**common, status=result.status)
    return NutritionReferenceNotFoundMealAnalysis(**common, status=result.status)

def get_leftover_analysis_service(database_session: Annotated[Session, Depends(get_db)], meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)]) -> LeftoverAnalysisService:
    return LeftoverAnalysisService(LeftoverAnalysisRepository(database_session), meal_analysis_service)


def leftover_analysis_response_from_model(analysis, meal) -> LeftoverAnalysisResponse:
    initial = LeftoverNutrition(calories=meal.total_calories, protein_g=meal.total_protein_g, carbohydrates_g=meal.total_carbohydrates_g, fat_g=meal.total_fat_g, fiber_g=meal.total_fiber_g)
    leftovers = LeftoverNutrition(calories=analysis.leftover_calories, protein_g=analysis.leftover_protein_g, carbohydrates_g=analysis.leftover_carbohydrates_g, fat_g=analysis.leftover_fat_g, fiber_g=analysis.leftover_fiber_g)
    consumed = LeftoverNutrition(calories=analysis.consumed_calories, protein_g=analysis.consumed_protein_g, carbohydrates_g=analysis.consumed_carbohydrates_g, fat_g=analysis.consumed_fat_g, fiber_g=analysis.consumed_fiber_g)
    return LeftoverAnalysisResponse(id=analysis.id, meal_id=analysis.meal_id, leftover_weight_grams=analysis.leftover_weight_grams, initial_nutrition=initial, leftover_nutrition=leftovers, consumed_nutrition=consumed, provenance=LeftoverAnalysisProvenance(source=analysis.source, recognized_food_name=analysis.recognized_food_name, source_reference=analysis.source_reference), created_at=analysis.created_at)


@router.post("/{meal_id}/leftover-analysis", response_model=LeftoverAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_leftover(meal_id: int, current_user: Annotated[User, Depends(get_current_user)], database_session: Annotated[Session, Depends(get_db)], leftover_analysis_service: Annotated[LeftoverAnalysisService, Depends(get_leftover_analysis_service)], leftover_weight_grams: Decimal = Form(ge=0, le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS), file: UploadFile | None = File(default=None)) -> LeftoverAnalysisResponse:
    meal = MealRepository(database_session).get_by_id_for_user(meal_id, current_user.id)
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal was not found.")
    image_bytes = content_type = None
    if leftover_weight_grams != 0:
        if file is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A food image is required for non-zero leftovers.")
        image_bytes, content_type = await read_validated_image(file)
    try:
        analysis = leftover_analysis_service.create(meal, leftover_weight_grams, image_bytes, content_type)
    except (DuplicateLeftoverAnalysisError, LeftoverAnalysisConflictError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None
    except LeftoverRecognitionError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Leftover recognition could not be completed: {error}.") from None
    return leftover_analysis_response_from_model(analysis, meal)


@router.get("/{meal_id}/leftover-analysis", response_model=LeftoverAnalysisResponse)
def get_leftover(meal_id: int, current_user: Annotated[User, Depends(get_current_user)], database_session: Annotated[Session, Depends(get_db)]) -> LeftoverAnalysisResponse:
    meal = MealRepository(database_session).get_by_id_for_user(meal_id, current_user.id)
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal was not found.")
    analysis = LeftoverAnalysisRepository(database_session).get_by_meal_id(meal.id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leftover analysis was not found.")
    return leftover_analysis_response_from_model(analysis, meal)


@router.post("/analyze", response_model=MealAnalysisResponse)
async def analyze_meal(
    file: UploadFile = File(description="JPEG, PNG, or WEBP meal image."),
    weight_grams: Decimal = Form(ge=0, le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS, allow_inf_nan=False),
    meal_analysis_service: MealAnalysisService = Depends(get_meal_analysis_service),
    principal: Annotated[MealOperationPrincipal | None, Depends(get_optional_meal_operation_principal)] = None,
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)] = None,
) -> MealAnalysisResponse:
    image_bytes, content_type = await read_validated_image(file)
    try:
        if principal is None:
            return meal_analysis_service.analyze(
                image_bytes=image_bytes, content_type=content_type, weight_grams=weight_grams,
            )
        composed = meal_analysis_service.analyze_composed(
            user_id=principal.user_id,
            image_bytes=image_bytes, content_type=content_type, measured_weight_grams=weight_grams,
            session_service=session_service,
        )
        if composed is not None:
            persisted = session_service.get_session_for_user(composed.session_id, principal.user_id)
            return composed_analysis_response(composed, persisted.expires_at)
        return meal_analysis_service.analyze(
            image_bytes=image_bytes,
            content_type=content_type,
            weight_grams=weight_grams,
        )
    except (FoodRecognitionProviderError, CompositeDishEstimatorError) as error:
        if error.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            detail = (
                "Composite dish estimation service is temporarily unavailable. Please try again later."
                if isinstance(error, CompositeDishEstimatorError)
                else "Food recognition service is temporarily unavailable. Please try again later."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            ) from None
        raise HTTPException(status_code=error.status_code, detail=error.detail) from None


@router.post("/analysis-sessions/{analysis_session_id}/selections", response_model=MealAnalysisResponse)
def select_meal_analysis_component(
    analysis_session_id: int,
    selection: MealAnalysisSelectionRequest,
    principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)],
    meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)],
) -> MealAnalysisResponse:
    try:
        result = meal_analysis_service.apply_selection(user_id=principal.user_id, session_id=analysis_session_id,
            component_id=str(selection.component_id), candidate_id=str(selection.candidate_id) if selection.candidate_id else None,
            candidate_name=selection.candidate_name, session_service=session_service)
        persisted = session_service.get_session_for_user(analysis_session_id, principal.user_id)
        return composed_analysis_response(result, persisted.expires_at)
    except MealAnalysisSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Meal analysis session was not found.") from None
    except MealAnalysisSessionExpiredError:
        raise HTTPException(status_code=410, detail="Meal analysis session has expired.") from None
    except MealAnalysisSessionConsumedError:
        raise HTTPException(status_code=409, detail="Meal analysis session was already consumed.") from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.put("/analysis-sessions/{analysis_session_id}/components/{component_id}/ingredients", response_model=MealAnalysisResponse)
def verify_meal_analysis_ingredients(
    analysis_session_id: int,
    component_id: str,
    verification: IngredientVerificationRequest,
    principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)],
    meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)],
) -> MealAnalysisResponse:
    try:
        result = meal_analysis_service.verify_ingredients(user_id=principal.user_id, session_id=analysis_session_id, component_id=component_id, ingredients=verification.ingredients, session_service=session_service)
        persisted = session_service.get_session_for_user(analysis_session_id, principal.user_id)
        return composed_analysis_response(result, persisted.expires_at)
    except MealAnalysisSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Meal analysis session was not found.") from None
    except MealAnalysisSessionExpiredError:
        raise HTTPException(status_code=410, detail="Meal analysis session has expired.") from None
    except MealAnalysisSessionConsumedError:
        raise HTTPException(status_code=409, detail="Meal analysis session was already consumed.") from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.post("/analysis-sessions/{analysis_session_id}/components/{component_id}/ingredients/selections", response_model=MealAnalysisResponse)
def select_ingredient_reference(
    analysis_session_id: int, component_id: str, selection: IngredientCandidateSelectionRequest,
    principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)],
    meal_analysis_service: Annotated[MealAnalysisService, Depends(get_meal_analysis_service)],
    session_service: Annotated[MealAnalysisSessionService, Depends(get_meal_analysis_session_service)],
) -> MealAnalysisResponse:
    try:
        result = meal_analysis_service.apply_ingredient_selection(user_id=principal.user_id, session_id=analysis_session_id, component_id=component_id, ingredient_id=str(selection.ingredient_id), candidate_id=str(selection.candidate_id), session_service=session_service)
        persisted = session_service.get_session_for_user(analysis_session_id, principal.user_id)
        return composed_analysis_response(result, persisted.expires_at)
    except MealAnalysisSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Meal analysis session was not found.") from None
    except MealAnalysisSessionExpiredError:
        raise HTTPException(status_code=410, detail="Meal analysis session has expired.") from None
    except MealAnalysisSessionConsumedError:
        raise HTTPException(status_code=409, detail="Meal analysis session was already consumed.") from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


def _legacy_nutrition_from_item(item) -> NutrientValues:
    return NutrientValues(
        calories=item.calculated_calories,
        protein_g=item.calculated_protein_g,
        carbohydrates_g=item.calculated_carbohydrates_g,
        fat_g=item.calculated_fat_g,
        fiber_g=item.calculated_fiber_g,
    )


def _portion_nutrition_from_item(item) -> PortionNutrition:
    return PortionNutrition(
        **_legacy_nutrition_from_item(item).model_dump(),
        saturated_fat_g=item.calculated_saturated_fat_g,
        sugars_g=item.calculated_sugars_g,
        sodium_mg=item.calculated_sodium_mg,
        cholesterol_mg=item.calculated_cholesterol_mg,
        omega_3_g=item.calculated_omega_3_g,
        omega_6_g=item.calculated_omega_6_g,
        calcium_mg=item.calculated_calcium_mg,
        potassium_mg=item.calculated_potassium_mg,
        zinc_mg=item.calculated_zinc_mg,
        iron_mg=item.calculated_iron_mg,
        magnesium_mg=item.calculated_magnesium_mg,
        energy_kj=derive_energy_kj(item.calculated_calories),
        phosphorus_mg=item.calculated_phosphorus_mg,
        vitamin_b6_mg=item.calculated_vitamin_b6_mg,
        niacin_mg=item.calculated_niacin_mg,
        vitamin_a_mcg_rae=item.calculated_vitamin_a_mcg_rae,
        vitamin_b12_mcg=item.calculated_vitamin_b12_mcg,
        vitamin_c_mg=item.calculated_vitamin_c_mg,
        vitamin_d_mcg=item.calculated_vitamin_d_mcg,
        folate_mcg_dfe=item.calculated_folate_mcg_dfe,
    )


def _additional_totals_from_items(items) -> AdditionalNutrientValues:
    """Return a complete total only when every immutable item snapshot is known."""
    snapshot_fields = {
        "saturated_fat_g": "calculated_saturated_fat_g",
        "sugars_g": "calculated_sugars_g",
        "sodium_mg": "calculated_sodium_mg",
        "cholesterol_mg": "calculated_cholesterol_mg",
        "omega_3_g": "calculated_omega_3_g",
        "omega_6_g": "calculated_omega_6_g",
        "calcium_mg": "calculated_calcium_mg",
        "potassium_mg": "calculated_potassium_mg",
        "zinc_mg": "calculated_zinc_mg",
        "iron_mg": "calculated_iron_mg",
        "magnesium_mg": "calculated_magnesium_mg",
        "phosphorus_mg": "calculated_phosphorus_mg",
        "vitamin_b6_mg": "calculated_vitamin_b6_mg",
        "niacin_mg": "calculated_niacin_mg",
        "vitamin_a_mcg_rae": "calculated_vitamin_a_mcg_rae",
        "vitamin_b12_mcg": "calculated_vitamin_b12_mcg",
        "vitamin_c_mg": "calculated_vitamin_c_mg",
        "vitamin_d_mcg": "calculated_vitamin_d_mcg",
        "folate_mcg_dfe": "calculated_folate_mcg_dfe",
    }
    totals = {}
    for response_field, snapshot_field in snapshot_fields.items():
        values = [getattr(item, snapshot_field) for item in items]
        totals[response_field] = sum(values, Decimal("0")) if values and all(value is not None for value in values) else None
    totals["energy_kj"] = derive_energy_kj(sum((item.calculated_calories for item in items), Decimal("0"))) if items else None
    return AdditionalNutrientValues(**totals)


def meal_response_from_model(meal) -> MealResponse:
    return MealResponse(
        id=meal.id,
        recorded_at=meal.recorded_at,
        items=[MealItemResponse(id=item.id, food=CalculatedFood(id=item.food_id, name=item.food_name_snapshot), weight_grams=item.weight_grams, nutrition=_portion_nutrition_from_item(item), nutrition_source=MealItemNutritionSource(category=item.nutrition_source_type, name=item.nutrition_source_name_snapshot, reference=item.nutrition_source_reference_snapshot, is_estimated=item.nutrition_is_estimated), composite_estimation=item.composite_provenance_snapshot is not None) for item in meal.items],
        totals=MealTotals(calories=meal.total_calories, protein_g=meal.total_protein_g, carbohydrates_g=meal.total_carbohydrates_g, fat_g=meal.total_fat_g, fiber_g=meal.total_fiber_g, energy_kj=derive_energy_kj(meal.total_calories)),
        additional_totals=_additional_totals_from_items(meal.items),
    )


def meal_list_item_from_model(meal) -> MealListItem:
    return MealListItem(
        id=meal.id,
        recorded_at=meal.recorded_at,
        items=[MealListItemResponse(id=item.id, food=CalculatedFood(id=item.food_id, name=item.food_name_snapshot), weight_grams=item.weight_grams, nutrition=_legacy_nutrition_from_item(item)) for item in meal.items],
        totals=NutrientValues(calories=meal.total_calories, protein_g=meal.total_protein_g, carbohydrates_g=meal.total_carbohydrates_g, fat_g=meal.total_fat_g, fiber_g=meal.total_fiber_g),
    )


@router.post("", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create_meal(meal_request: MealCreateRequest, principal: Annotated[MealOperationPrincipal, Depends(require_meal_operation_principal)], meal_service: Annotated[MealService, Depends(get_meal_service)]) -> MealResponse:
    try:
        if meal_request.analysis_session_id is not None:
            return meal_response_from_model(meal_service.create_meal_from_analysis_session(meal_request.analysis_session_id, principal.user_id))
        if principal.authentication_mode == "device":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Devices may save only completed meal analysis sessions.")
        return meal_response_from_model(meal_service.create_meal(meal_request.items or [], principal.user_id))
    except MealFoodNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from None
    except MealAnalysisSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Meal analysis session was not found.") from None
    except MealAnalysisSessionExpiredError:
        raise HTTPException(status_code=410, detail="Meal analysis session has expired.") from None
    except (MealAnalysisSessionConsumedError, MealAnalysisSessionNotCalculatedError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get("", response_model=MealListResponse)
def list_meals(current_user: Annotated[User, Depends(get_current_user)], meal_service: Annotated[MealService, Depends(get_meal_service)], limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> MealListResponse:
    return MealListResponse(meals=[meal_list_item_from_model(meal) for meal in meal_service.list_meals(current_user.id, limit, offset)], limit=limit, offset=offset)


@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: int, current_user: Annotated[User, Depends(get_current_user)], meal_service: Annotated[MealService, Depends(get_meal_service)]) -> MealResponse:
    meal = meal_service.get_meal(meal_id, current_user.id)
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal was not found.")
    return meal_response_from_model(meal)
