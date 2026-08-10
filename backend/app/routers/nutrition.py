from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.repositories.food_repository import FoodRepository
from app.schemas.nutrition import (
    CalculatedFood,
    FoodListResponse,
    FoodResponse,
    PortionCalculationRequest,
    PortionCalculationResponse,
)
from app.services.nutrition_service import NutritionService

router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


def get_nutrition_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> NutritionService:
    """Provide a nutrition service scoped to the current database session."""
    return NutritionService(FoodRepository(database_session))


@router.get("/search", response_model=FoodListResponse)
def search_foods(
    q: Annotated[str, Query(min_length=1, max_length=160)],
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
) -> FoodListResponse:
    """Search canonical foods by case-insensitive display or normalized name."""
    foods = nutrition_service.search_foods(q)
    return FoodListResponse(foods=[FoodResponse.from_food(food) for food in foods])


@router.post("/calculate", response_model=PortionCalculationResponse)
def calculate_portion(
    calculation_request: PortionCalculationRequest,
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
) -> PortionCalculationResponse:
    """Calculate nutrition for a measured portion of a canonical food."""
    calculation = nutrition_service.calculate_portion(
        calculation_request.food_id,
        calculation_request.weight_grams,
    )
    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food record was not found.",
        )

    food, nutrition = calculation
    return PortionCalculationResponse(
        food=CalculatedFood(id=food.id, name=food.name),
        weight_grams=calculation_request.weight_grams,
        nutrition=nutrition,
    )


@router.get("/{food_id}", response_model=FoodResponse)
def get_food(
    food_id: int,
    nutrition_service: Annotated[NutritionService, Depends(get_nutrition_service)],
) -> FoodResponse:
    """Return one canonical nutrition reference record by identifier."""
    food = nutrition_service.get_food(food_id)
    if food is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food record was not found.",
        )
    return FoodResponse.from_food(food)
