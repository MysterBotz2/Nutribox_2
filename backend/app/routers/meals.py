from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.food_repository import FoodRepository
from app.repositories.meal_repository import MealRepository
from app.routers.nutrition import get_nutrition_service
from app.schemas.meal import (
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
from app.schemas.nutrition import AdditionalNutrientValues, CalculatedFood, NutrientValues, PortionNutrition
from app.services.food_recognition_provider import FoodRecognitionProvider
from app.services.food_recognition_selector import get_food_recognition_provider
from app.services.image_validation import read_validated_image
from app.services.meal_analysis_service import MealAnalysisService
from app.services.meal_service import MealFoodNotFoundError, MealService
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/api/meals", tags=["meals"])


def get_meal_analysis_service(
    provider: Annotated[FoodRecognitionProvider, Depends(get_food_recognition_provider)],
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
) -> MealAnalysisService:
    return MealAnalysisService(provider, nutrition_service)


def get_meal_service(database_session: Annotated[Session, Depends(get_db)]) -> MealService:
    return MealService(
        NutritionService(FoodRepository(database_session)),
        MealRepository(database_session),
    )


@router.post("/analyze", response_model=MealAnalysisResponse)
async def analyze_meal(
    file: UploadFile = File(description="JPEG, PNG, or WEBP meal image."),
    weight_grams: Decimal = Form(ge=0, le=MAXIMUM_PROTOTYPE_WEIGHT_GRAMS, allow_inf_nan=False),
    meal_analysis_service: MealAnalysisService = Depends(get_meal_analysis_service),
) -> MealAnalysisResponse:
    image_bytes, content_type = await read_validated_image(file)
    return meal_analysis_service.analyze(image_bytes=image_bytes, content_type=content_type, weight_grams=weight_grams)


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
    return AdditionalNutrientValues(**totals)


def meal_response_from_model(meal) -> MealResponse:
    return MealResponse(
        id=meal.id,
        recorded_at=meal.recorded_at,
        items=[MealItemResponse(id=item.id, food=CalculatedFood(id=item.food_id, name=item.food_name_snapshot), weight_grams=item.weight_grams, nutrition=_portion_nutrition_from_item(item), nutrition_source=MealItemNutritionSource(category=item.nutrition_source_type, name=item.nutrition_source_name_snapshot, reference=item.nutrition_source_reference_snapshot, is_estimated=item.nutrition_is_estimated)) for item in meal.items],
        totals=MealTotals(calories=meal.total_calories, protein_g=meal.total_protein_g, carbohydrates_g=meal.total_carbohydrates_g, fat_g=meal.total_fat_g, fiber_g=meal.total_fiber_g),
        additional_totals=_additional_totals_from_items(meal.items),
    )


def meal_list_item_from_model(meal) -> MealListItem:
    return MealListItem(
        id=meal.id,
        recorded_at=meal.recorded_at,
        items=[MealListItemResponse(id=item.id, food=CalculatedFood(id=item.food_id, name=item.food_name_snapshot), weight_grams=item.weight_grams, nutrition=_legacy_nutrition_from_item(item)) for item in meal.items],
        totals=MealTotals(calories=meal.total_calories, protein_g=meal.total_protein_g, carbohydrates_g=meal.total_carbohydrates_g, fat_g=meal.total_fat_g, fiber_g=meal.total_fiber_g),
    )


@router.post("", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create_meal(meal_request: MealCreateRequest, current_user: Annotated[User, Depends(get_current_user)], meal_service: Annotated[MealService, Depends(get_meal_service)]) -> MealResponse:
    try:
        return meal_response_from_model(meal_service.create_meal(meal_request.items, current_user.id))
    except MealFoodNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from None


@router.get("", response_model=MealListResponse)
def list_meals(current_user: Annotated[User, Depends(get_current_user)], meal_service: Annotated[MealService, Depends(get_meal_service)], limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> MealListResponse:
    return MealListResponse(meals=[meal_list_item_from_model(meal) for meal in meal_service.list_meals(current_user.id, limit, offset)], limit=limit, offset=offset)


@router.get("/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: int, current_user: Annotated[User, Depends(get_current_user)], meal_service: Annotated[MealService, Depends(get_meal_service)]) -> MealResponse:
    meal = meal_service.get_meal(meal_id, current_user.id)
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal was not found.")
    return meal_response_from_model(meal)
