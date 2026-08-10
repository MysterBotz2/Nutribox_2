from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRegistrationRequest
from app.services.security import hash_password, normalize_email, verify_dummy_password, verify_password


class DuplicateEmailError(ValueError):
    """Raised when a normalized email is already registered."""


class InvalidCredentialsError(ValueError):
    """Raised for any failed authentication attempt without revealing its cause."""


class AuthService:
    """Registration and credential verification without route-level crypto or SQL."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    def register(self, request: UserRegistrationRequest) -> User:
        session = self._users.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        try:
            with transaction:
                email = normalize_email(str(request.email))
                if self._users.get_by_email(email) is not None:
                    raise DuplicateEmailError("An account with this email already exists.")
                user = User(
                    email=email,
                    password_hash=hash_password(request.password),
                    first_name=request.first_name,
                    last_name=request.last_name,
                )
                self._users.add(user)
                session.flush()
        except IntegrityError as error:
            raise DuplicateEmailError("An account with this email already exists.") from error
        return user

    def authenticate(self, email: str, password: str) -> User:
        user = self._users.get_by_email(normalize_email(email))
        if user is None:
            verify_dummy_password(password)
            raise InvalidCredentialsError("Incorrect email or password.")
        if not verify_password(password, user.password_hash) or not user.is_active:
            raise InvalidCredentialsError("Incorrect email or password.")
        return user
