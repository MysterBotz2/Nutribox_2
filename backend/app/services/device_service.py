from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceReading:
    """A hardware-agnostic device sensor reading."""

    weight_grams: float
    temperature_celsius: float
    source: str


class DeviceService(ABC):
    """Boundary used by the API to obtain a device reading."""

    @abstractmethod
    def read(
        self, *, weight_grams: float, temperature_celsius: float
    ) -> DeviceReading:
        """Return a reading from the configured device implementation."""
