from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.nutrition_profile_repository import NutritionProfileRepository
from app.schemas.auth import PublicUser
from app.schemas.profile import NutritionProfileResponse, NutritionProfileUpdateRequest
from app.services.nutrition_profile_service import NutritionProfileService

router = APIRouter(prefix="/api/users", tags=["users"])


def get_nutrition_profile_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> NutritionProfileService:
    return NutritionProfileService(NutritionProfileRepository(database_session))


@router.get("/me", response_model=PublicUser)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> PublicUser:
    return PublicUser.model_validate(current_user)


@router.get("/me/profile", response_model=NutritionProfileResponse)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[NutritionProfileService, Depends(get_nutrition_profile_service)],
) -> NutritionProfileResponse:
    profile = profile_service.get_profile(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutrition profile was not found.")
    return NutritionProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=NutritionProfileResponse)
def replace_my_profile(
    request: NutritionProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    profile_service: Annotated[NutritionProfileService, Depends(get_nutrition_profile_service)],
) -> NutritionProfileResponse:
    """Create a profile or replace all profile values for the current user."""
    return NutritionProfileResponse.model_validate(
        profile_service.replace_profile(current_user.id, request)
    )
