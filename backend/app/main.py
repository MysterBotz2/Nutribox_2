from fastapi import FastAPI

from app.routers.health import router as health_router

app = FastAPI(title="Nutri-Box API")
app.include_router(health_router)


@app.get("/", tags=["service"])
def get_root() -> dict[str, str]:
    """Return basic service information."""
    return {"name": "Nutri-Box API", "status": "running"}
