from typing import Literal

from pydantic import BaseModel, Field

MAXIMUM_WEIGHT_GRAMS = 5000.0
MINIMUM_TEMPERATURE_CELSIUS = -50.0
MAXIMUM_TEMPERATURE_CELSIUS = 150.0


class DeviceSimulationRequest(BaseModel):
    """Validated manual values for the development device simulation."""

    weight_grams: float = Field(
        ge=0,
        le=MAXIMUM_WEIGHT_GRAMS,
        allow_inf_nan=False,
        description="Development prototype weight in grams, from 0 to 5000.",
    )
    temperature_celsius: float = Field(
        ge=MINIMUM_TEMPERATURE_CELSIUS,
        le=MAXIMUM_TEMPERATURE_CELSIUS,
        allow_inf_nan=False,
        description=(
            "Software sanity range from -50 to 150 degrees Celsius; "
            "this is not a hardware specification."
        ),
    )


class DeviceReadingResponse(BaseModel):
    """A normalized sensor reading returned by a device service."""

    weight_grams: float
    temperature_celsius: float
    source: Literal["simulated"]
