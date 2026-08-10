import math
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routers.ai import router as ai_router
from app.routers.auth import router as auth_router
from app.routers.device import router as device_router
from app.routers.health import router as health_router
from app.routers.meals import router as meals_router
from app.routers.nutrition import router as nutrition_router
from app.routers.users import router as users_router

app = FastAPI(title="Nutri-Box API")
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(device_router)
app.include_router(ai_router)
app.include_router(nutrition_router)
app.include_router(meals_router)


def _json_safe_validation_detail(value: Any) -> Any:
    """Replace non-finite floats before returning request validation errors."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {key: _json_safe_validation_detail(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_validation_detail(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _: Request, exception: RequestValidationError
) -> JSONResponse:
    """Return valid JSON when malformed input contains NaN or infinity."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": _json_safe_validation_detail(exception.errors())},
    )


@app.get("/", tags=["service"])
def get_root() -> dict[str, str]:
    """Return basic service information."""
    return {"name": "Nutri-Box API", "status": "running"}
