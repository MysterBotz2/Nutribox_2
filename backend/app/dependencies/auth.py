from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.security import SecurityConfigurationError, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    database_session: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve an active account from a signed bearer access token."""
    try:
        user_id = decode_access_token(token)
    except SecurityConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        ) from None
    except ValueError:
        raise _credentials_exception() from None

    user = UserRepository(database_session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _credentials_exception()
    return user


def get_optional_current_user(
    token: Annotated[str | None, Depends(optional_oauth2_scheme)],
    database_session: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Return no user for a legacy anonymous request; reject malformed bearer tokens."""
    if token is None:
        return None
    try:
        user_id = decode_access_token(token)
    except SecurityConfigurationError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is not configured.") from None
    except ValueError:
        raise _credentials_exception() from None
    user = UserRepository(database_session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise _credentials_exception()
    return user
