from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas.nutrition_target import TargetNutrientValues, TargetSourceType
from app.schemas.progress import (
    DailyProgressResponse,
    ProgressSummaryResponse,
    TargetStatusResponse,
)


@dataclass(frozen=True, slots=True)
class NutritionCoachProfileContext:
    activity_level: str | None
    nutrition_goal: str | None
    dietary_restrictions: tuple[str, ...]
    allergies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NutritionCoachTargetContext:
    values: TargetNutrientValues
    source_type: TargetSourceType


@dataclass(frozen=True, slots=True)
class NutritionCoachContext:
    """Minimal trusted context passed to a coach provider; it has no identity or DB access."""

    timezone: str
    profile: NutritionCoachProfileContext | None
    target: NutritionCoachTargetContext | None
    today: DailyProgressResponse
    target_comparison: TargetStatusResponse
    weekly: ProgressSummaryResponse
    question: str | None
    conversation_history: tuple["NutritionCoachChatTurn", ...] = ()


@dataclass(frozen=True, slots=True)
class NutritionCoachChatTurn:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class NutritionCoachResult:
    message: str
    highlights: tuple[str, ...]
    provider: str


class NutritionCoachUnavailable(RuntimeError):
    """Provider-neutral failure for an unavailable coach implementation."""


class NutritionCoachInvalidResponse(RuntimeError):
    """Provider-neutral failure for a malformed provider result."""


class NutritionCoachProvider(ABC):
    """Capability boundary for vendor-specific nutrition coaching adapters."""

    @abstractmethod
    async def generate_guidance(self, context: NutritionCoachContext) -> NutritionCoachResult:
        """Translate a prepared Nutri-Box context into safe human-readable guidance."""

    async def generate_chat_reply(self, context: NutritionCoachContext) -> NutritionCoachResult:
        """Generate a reply using bounded, trusted conversation context."""
        return await self.generate_guidance(context)
