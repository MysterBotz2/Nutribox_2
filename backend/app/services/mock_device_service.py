from app.services.device_service import DeviceReading, DeviceService


class MockDeviceService(DeviceService):
    """Development-only device service that returns manually supplied values."""

    def read(
        self, *, weight_grams: float, temperature_celsius: float
    ) -> DeviceReading:
        return DeviceReading(
            weight_grams=weight_grams,
            temperature_celsius=temperature_celsius,
            source="simulated",
        )
