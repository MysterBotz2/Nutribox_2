"""Narrow dual authentication for owner-scoped meal operations."""

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import get_db
from app.models.user import User
from app.repositories.device_pairing_repository import DevicePairingRepository
from app.repositories.user_repository import UserRepository
from app.services.device_pairing_service import DevicePairingService
from app.services.security import SecurityConfigurationError, decode_access_token
from app.dependencies.auth import optional_oauth2_scheme


optional_device_token_scheme = APIKeyHeader(name="X-Device-Token", auto_error=False)


@dataclass(frozen=True, slots=True)
class MealOperationPrincipal:
    user_id: int
    authentication_mode: Literal["bearer", "device"]
    device_id: int | None = None


def _bearer_failure() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.", headers={"WWW-Authenticate": "Bearer"})


def _device_failure() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device authentication failed.")


def get_optional_meal_operation_principal(
    token: Annotated[str | None, Security(optional_oauth2_scheme)] = None,
    x_device_token: Annotated[str | None, Security(optional_device_token_scheme)] = None,
    authorization: Annotated[str | None, Header()] = None,
    database_session: Annotated[Session, Depends(get_db)] = None,
) -> MealOperationPrincipal | None:
    """Resolve one credential type; never merge a user and device identity."""
    if token and x_device_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide either bearer or device credentials, not both.")
    if authorization and token is None:
        raise _bearer_failure()
    if token:
        try:
            user_id = decode_access_token(token)
        except SecurityConfigurationError:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured.") from None
        except ValueError:
            raise _bearer_failure() from None
        user = UserRepository(database_session).get_by_id(user_id)
        if user is None or not user.is_active:
            raise _bearer_failure()
        return MealOperationPrincipal(user_id=user.id, authentication_mode="bearer")
    if x_device_token:
        if not settings.device_pairing_secret:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Device pairing is not configured.")
        device = DevicePairingService(
            DevicePairingRepository(database_session), settings.device_pairing_secret, settings.device_pairing_ttl_seconds
        ).authenticated_device(x_device_token)
        if device is None:
            raise _device_failure()
        user = UserRepository(database_session).get_by_id(device.user_id)
        if user is None or not user.is_active:
            raise _device_failure()
        return MealOperationPrincipal(user_id=device.user_id, authentication_mode="device", device_id=device.id)
    return None


def require_meal_operation_principal(
    principal: Annotated[MealOperationPrincipal | None, Depends(get_optional_meal_operation_principal)],
) -> MealOperationPrincipal:
    if principal is None:
        raise _bearer_failure()
    return principal
