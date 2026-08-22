from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None: raise ValueError("Datetime values must include a timezone offset.")
    return value.astimezone(timezone.utc)
class WeightEntryWrite(BaseModel):
    model_config=ConfigDict(extra="forbid")
    weight_kg: Decimal=Field(gt=0, le=500, allow_inf_nan=False)
    measured_at: datetime
    @field_validator("measured_at")
    @classmethod
    def aware(cls,v): return utc(v)
class WeightEntryResponse(WeightEntryWrite):
    model_config=ConfigDict(from_attributes=True)
    id:int
    created_at:datetime
    @field_validator("created_at")
    @classmethod
    def created_utc(cls,v): return utc(v)
class WeightEntryList(BaseModel): entries:list[WeightEntryResponse]; limit:int; offset:int
