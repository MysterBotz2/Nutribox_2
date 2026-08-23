"""Gemini implementation of the provider-neutral Nutri-Box coaching capability."""

import asyncio
from dataclasses import asdict

from google import genai
from google.genai import errors, types

from app.services.nutrition_coach_provider import NutritionCoachContext, NutritionCoachProvider, NutritionCoachResult, NutritionCoachUnavailable, NutritionCoachInvalidResponse

_SYSTEM = """You are Nutri-Box, a concise nutrition assistant. Use only supplied Nutri-Box facts for a user's logged nutrition and targets. Never invent logged values or personalized targets. Clearly distinguish general education from stored targets. Do not diagnose, prescribe medication, claim to treat or cure disease, or give clinical advice. Acknowledge missing information and encourage qualified professional care when appropriate."""


class GeminiNutritionCoachProvider(NutritionCoachProvider):
    def __init__(self, *, api_key: str, model: str, timeout_seconds: int, client=None) -> None:
        self._model = model
        self._client = client or genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_seconds * 1000))

    async def generate_guidance(self, context: NutritionCoachContext) -> NutritionCoachResult:
        reply = await self.generate_chat_reply(context)
        highlights = [f"{context.today.meal_count} meal(s) are recorded for the selected day."]
        highlights.append(
            "Configured nutrition targets were included for neutral comparison."
            if context.target is not None
            else "No configured nutrition targets are available."
        )
        return NutritionCoachResult(message=reply.message, highlights=tuple(highlights), provider=reply.provider)

    async def generate_chat_reply(self, context: NutritionCoachContext) -> NutritionCoachResult:
        payload = {"timezone": context.timezone, "profile": asdict(context.profile) if context.profile else None, "target": asdict(context.target) if context.target else None, "today": context.today.model_dump(mode="json"), "target_comparison": context.target_comparison.model_dump(mode="json"), "weekly": context.weekly.model_dump(mode="json"), "history": [asdict(turn) for turn in context.conversation_history], "user_message": context.question}
        try:
            response = await asyncio.to_thread(self._client.models.generate_content, model=self._model, contents=[_SYSTEM, str(payload)], config=types.GenerateContentConfig(temperature=0.2))
            text = getattr(response, "text", None)
        except errors.APIError as error:
            raise NutritionCoachUnavailable("Nutrition coach provider is unavailable.") from error
        except Exception as error:
            raise NutritionCoachUnavailable("Nutrition coach provider is unavailable.") from error
        if not isinstance(text, str) or not text.strip():
            raise NutritionCoachInvalidResponse("Nutrition coach provider returned an invalid response.")
        return NutritionCoachResult(message=text.strip(), highlights=(), provider="gemini")
