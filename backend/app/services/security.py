from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

_password_hasher = PasswordHash.recommended()
_DUMMY_PASSWORD_HASH = _password_hasher.hash("nutri-box-invalid-login-placeholder")


class SecurityConfigurationError(RuntimeError):
    """Raised when authentication is invoked without safe JWT configuration."""


def normalize_email(email: str) -> str:
    """Normalize account lookup keys by trimming whitespace and case-folding."""
    return email.strip().casefold()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hasher.verify(password, password_hash)


def verify_dummy_password(password: str) -> None:
    """Perform equivalent password work when an account lookup finds no user."""
    _password_hasher.verify(password, _DUMMY_PASSWORD_HASH)


def _security_settings() -> tuple[str, str, int]:
    secret_key = settings.jwt_secret_key
    if not secret_key or len(secret_key) < 32 or settings.jwt_algorithm != "HS256":
        raise SecurityConfigurationError("Authentication is not configured.")
    return secret_key, settings.jwt_algorithm, settings.access_token_expire_minutes


def create_access_token(user_id: int) -> str:
    secret_key, algorithm, expires_in_minutes = _security_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret_key, algorithm=algorithm)


def decode_access_token(token: str) -> int:
    secret_key, algorithm, _ = _security_settings()
    try:
        subject = jwt.decode(token, secret_key, algorithms=[algorithm]).get("sub")
        if not isinstance(subject, str) or not subject.isdecimal() or int(subject) <= 0:
            raise InvalidTokenError("Token subject is invalid.")
    except InvalidTokenError as error:
        raise ValueError("Token is invalid.") from error
    return int(subject)
