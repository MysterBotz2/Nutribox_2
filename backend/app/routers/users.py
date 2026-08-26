from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.nutrition_profile_repository import NutritionProfileRepository
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.repositories.profile_consent_repository import ProfileConsentRepository
from app.repositories.sensitive_profile_repository import SensitiveProfileRepository
from app.schemas.auth import PublicUser
from app.schemas.profile import NutritionProfileResponse, NutritionProfileUpdateRequest
from app.schemas.nutrition_target import NutritionTargetResponse, NutritionTargetUpdateRequest
from app.schemas.onboarding import OnboardingStatusResponse
from app.schemas.sensitive_profile import (
    ProfileConsentResponse,
    ProfileConsentState,
    ProfileConsentUpdateRequest,
    SensitiveProfileResponse,
    SensitiveProfileUpdateRequest,
)
from app.services.profile_consent_service import ProfileConsentService
from app.services.sensitive_profile_service import SensitiveProfileService
from app.services.nutrition_profile_service import NutritionProfileService
from app.services.nutrition_target_service import NutritionTargetService
from app.services.onboarding_service import OnboardingService
from app.repositories.device_pairing_repository import DevicePairingRepository
from app.schemas.device_pairing import PairDeviceRequest, PairedDeviceListResponse, PairedDeviceResponse
from app.routers.device_pairing import device_response, get_pairing_service
from app.services.device_pairing_service import DevicePairingService, PairingError
from app.dependencies.user_recipes import get_user_recipe_service
from app.schemas.user_recipe import (
    UserRecipeListResponse,
    UserRecipeResponse,
    user_recipe_response_from_model,
)
from app.services.user_recipe_service import UserRecipeNotFoundError, UserRecipeService

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/me/devices/pair", response_model=PairedDeviceResponse, status_code=status.HTTP_201_CREATED)
def pair_my_device(request: PairDeviceRequest, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[DevicePairingService, Depends(get_pairing_service)]):
    try: return device_response(service.claim(current_user.id, request.pairing_code))
    except PairingError as error: raise HTTPException(status_code=422, detail=str(error)) from None

@router.get("/me/devices", response_model=PairedDeviceListResponse)
def list_my_devices(current_user: Annotated[User, Depends(get_current_user)], database_session: Annotated[Session, Depends(get_db)]):
    return PairedDeviceListResponse(devices=[device_response(device) for device in DevicePairingRepository(database_session).list_for_user(current_user.id)])

@router.delete("/me/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_my_device(device_id: int, current_user: Annotated[User, Depends(get_current_user)], service: Annotated[DevicePairingService, Depends(get_pairing_service)]):
    device=service._repo.get_device_for_user(device_id,current_user.id)
    if device is None: raise HTTPException(status_code=404,detail="Device was not found.")
    service.revoke(device)


def get_nutrition_profile_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> NutritionProfileService:
    return NutritionProfileService(NutritionProfileRepository(database_session))


def get_nutrition_target_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> NutritionTargetService:
    return NutritionTargetService(NutritionTargetRepository(database_session))


def get_profile_consent_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> ProfileConsentService:
    return ProfileConsentService(
        ProfileConsentRepository(database_session), SensitiveProfileRepository(database_session)
    )


def get_sensitive_profile_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> SensitiveProfileService:
    consent_service = get_profile_consent_service(database_session)
    return SensitiveProfileService(SensitiveProfileRepository(database_session), consent_service)


def get_onboarding_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> OnboardingService:
    return OnboardingService(
        NutritionProfileRepository(database_session),
        SensitiveProfileRepository(database_session),
        get_profile_consent_service(database_session),
    )


@router.get("/me", response_model=PublicUser)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> PublicUser:
    return PublicUser.model_validate(current_user)


@router.get("/me/recipes", response_model=UserRecipeListResponse)
def list_my_recipes(
    current_user: Annotated[User, Depends(get_current_user)],
    recipe_service: Annotated[UserRecipeService, Depends(get_user_recipe_service)],
) -> UserRecipeListResponse:
    return UserRecipeListResponse(
        recipes=[user_recipe_response_from_model(recipe) for recipe in recipe_service.list_for_user(current_user.id)]
    )


@router.get("/me/recipes/{recipe_id}", response_model=UserRecipeResponse)
def get_my_recipe(
    recipe_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    recipe_service: Annotated[UserRecipeService, Depends(get_user_recipe_service)],
) -> UserRecipeResponse:
    try:
        return user_recipe_response_from_model(recipe_service.get_for_user(recipe_id, current_user.id))
    except UserRecipeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal recipe was not found.") from None


@router.delete("/me/recipes/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_recipe(
    recipe_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    recipe_service: Annotated[UserRecipeService, Depends(get_user_recipe_service)],
) -> None:
    try:
        recipe_service.delete_for_user(recipe_id, current_user.id)
    except UserRecipeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal recipe was not found.") from None


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


@router.get("/me/onboarding-status", response_model=OnboardingStatusResponse)
def get_my_onboarding_status(
    current_user: Annotated[User, Depends(get_current_user)],
    onboarding_service: Annotated[OnboardingService, Depends(get_onboarding_service)],
) -> OnboardingStatusResponse:
    """Return derived mobile-onboarding completion metadata for the token owner."""
    return onboarding_service.status_for_user(current_user.id)


@router.get("/me/profile-consent", response_model=ProfileConsentResponse)
def get_my_profile_consent(
    current_user: Annotated[User, Depends(get_current_user)],
    consent_service: Annotated[ProfileConsentService, Depends(get_profile_consent_service)],
) -> ProfileConsentResponse:
    consent = consent_service.get_consent(current_user.id)
    if consent is None:
        return ProfileConsentResponse(
            user_id=current_user.id,
            sensitive_storage=ProfileConsentState.NOT_ASKED,
            personalization=ProfileConsentState.NOT_ASKED,
            ai_context=ProfileConsentState.NOT_ASKED,
            updated_at=None,
        )
    return ProfileConsentResponse.model_validate(consent)


@router.put("/me/profile-consent", response_model=ProfileConsentResponse)
def replace_my_profile_consent(
    request: ProfileConsentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    consent_service: Annotated[ProfileConsentService, Depends(get_profile_consent_service)],
) -> ProfileConsentResponse:
    """Replace independent product permission states for the authenticated user."""
    return ProfileConsentResponse.model_validate(
        consent_service.replace_consent(current_user.id, request)
    )


@router.get("/me/sensitive-profile", response_model=SensitiveProfileResponse)
def get_my_sensitive_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    sensitive_profile_service: Annotated[SensitiveProfileService, Depends(get_sensitive_profile_service)],
) -> SensitiveProfileResponse:
    context = sensitive_profile_service.get_context(current_user.id)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sensitive profile was not found."
        )
    return SensitiveProfileResponse.model_validate(context)


@router.put("/me/sensitive-profile", response_model=SensitiveProfileResponse)
def replace_my_sensitive_profile(
    request: SensitiveProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    sensitive_profile_service: Annotated[SensitiveProfileService, Depends(get_sensitive_profile_service)],
) -> SensitiveProfileResponse:
    """Replace active sensitive declarations when storage consent is granted."""
    return SensitiveProfileResponse.model_validate(
        sensitive_profile_service.replace_context(current_user.id, request)
    )


@router.get("/me/targets", response_model=NutritionTargetResponse)
def get_my_targets(
    current_user: Annotated[User, Depends(get_current_user)],
    target_service: Annotated[NutritionTargetService, Depends(get_nutrition_target_service)],
) -> NutritionTargetResponse:
    target = target_service.get_target(current_user.id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutrition targets were not found.")
    return NutritionTargetResponse.model_validate(target)


@router.put("/me/targets", response_model=NutritionTargetResponse)
def replace_my_targets(
    request: NutritionTargetUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    target_service: Annotated[NutritionTargetService, Depends(get_nutrition_target_service)],
) -> NutritionTargetResponse:
    """Create targets or replace all target values for the current user."""
    return NutritionTargetResponse.model_validate(
        target_service.replace_target(current_user.id, request)
    )
