from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.device import DeviceReadingResponse, DeviceSimulationRequest
from app.services.device_service import DeviceService
from app.services.mock_device_service import MockDeviceService

router = APIRouter(prefix="/api/device", tags=["device"])

_device_service = MockDeviceService()


def get_device_service() -> DeviceService:
    """Provide the development device implementation for API requests."""
    return _device_service


@router.post("/simulate", response_model=DeviceReadingResponse)
def simulate_device_reading(
    simulation: DeviceSimulationRequest,
    device_service: Annotated[DeviceService, Depends(get_device_service)],
) -> DeviceReadingResponse:
    """Return a validated simulated reading without persisting it."""
    reading = device_service.read(
        weight_grams=simulation.weight_grams,
        temperature_celsius=simulation.temperature_celsius,
    )
    return DeviceReadingResponse(
        weight_grams=reading.weight_grams,
        temperature_celsius=reading.temperature_celsius,
        source=reading.source,
    )
