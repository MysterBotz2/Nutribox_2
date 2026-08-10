from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.database import database

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=None)
def get_health() -> dict[str, str] | JSONResponse:
    """Return service health without exposing database connection details."""
    if database.check_database_connection():
        return {"status": "healthy", "database": "connected"}

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "database": "disconnected"},
    )
