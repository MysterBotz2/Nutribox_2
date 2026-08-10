from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessTokenResponse, PublicUser, UserRegistrationRequest
from app.services.auth_service import AuthService, DuplicateEmailError, InvalidCredentialsError
from app.services.security import SecurityConfigurationError, create_access_token

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def get_auth_service(database_session: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(UserRepository(database_session))


@router.post("/register", response_model=PublicUser, status_code=status.HTTP_201_CREATED)
def register_user(
    registration: UserRegistrationRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> PublicUser:
    try:
        return PublicUser.model_validate(auth_service.register(registration))
    except DuplicateEmailError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from None


@router.post("/token", response_model=AccessTokenResponse)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AccessTokenResponse:
    try:
        user = auth_service.authenticate(form_data.username, form_data.password)
        return AccessTokenResponse(access_token=create_access_token(user.id))
    except SecurityConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        ) from None
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
