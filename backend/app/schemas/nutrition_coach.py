from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NutritionCoachRequest(BaseModel):
    """Optional user-facing context; authoritative nutrition values stay server-side."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str | None = Field(default=None, max_length=500)


class NutritionCoachResponse(BaseModel):
    message: str
    highlights: list[str] = Field(min_length=1, max_length=10)
    provider: str
    generated_at: datetime
