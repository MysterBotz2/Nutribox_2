from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime values must include a timezone offset.")
    return value.astimezone(timezone.utc)


class ScheduledMealWriteRequest(BaseModel):
    """Full replacement input for a planned meal label and its scheduled instant."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    scheduled_for: datetime
    title: str = Field(min_length=1, max_length=160)
    notes: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("scheduled_for")
    @classmethod
    def scheduled_for_must_include_timezone(cls, value: datetime) -> datetime:
        return _require_timezone(value)


class ScheduledMealCreateRequest(ScheduledMealWriteRequest):
    pass


class ScheduledMealUpdateRequest(ScheduledMealWriteRequest):
    pass


class ScheduledMealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_for: datetime
    title: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("scheduled_for", "created_at", "updated_at")
    @classmethod
    def serialize_timestamps_in_utc(cls, value: datetime) -> datetime:
        return _require_timezone(value)


class ScheduledMealListResponse(BaseModel):
    scheduled_meals: list[ScheduledMealResponse]
    limit: int
    offset: int
