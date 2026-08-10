from collections.abc import Generator

from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a database operation is requested without DATABASE_URL."""


engine: Engine | None = (
    create_engine(settings.database_url, pool_pre_ping=True)
    if settings.database_url
    else None
)
SessionLocal: sessionmaker[Session] | None = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    if engine is not None
    else None
)


def check_database_connection() -> bool:
    """Return whether PostgreSQL can accept a simple connection query."""
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False

    return True


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session for future API routes."""
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured.",
        )

    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
