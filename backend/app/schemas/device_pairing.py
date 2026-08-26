from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class PairingStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    device_name: str = Field(default="NutriBox Pi", min_length=1, max_length=160)

class PairingStartResponse(BaseModel):
    session_id: str; pairing_code: str; device_token: str; expires_at: datetime
class PairingStatusRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64); device_token: str = Field(min_length=20, max_length=256)
class PairingStatusResponse(BaseModel):
    status: str; device_id: int | None = None
class PairDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pairing_code: str = Field(pattern=r"^\d{6}$")
class PairedDeviceResponse(BaseModel):
    id: int; name: str; device_type: str; paired_at: datetime; last_seen_at: datetime | None = None
class DeviceIdentityResponse(PairedDeviceResponse):
    owner_first_name: str = Field(min_length=1, max_length=80)
class PairedDeviceListResponse(BaseModel):
    devices: list[PairedDeviceResponse]
