from app.services.nutrition_coach_provider import (
    NutritionCoachContext,
    NutritionCoachProvider,
    NutritionCoachResult,
)

_MEDICAL_TERMS = ("diagnos", "medication", "treat", "disease", "diabetes", "hypertension")


class MockNutritionCoachProvider(NutritionCoachProvider):
    """Deterministic development-only coach that never claims real AI reasoning."""

    async def generate_guidance(self, context: NutritionCoachContext) -> NutritionCoachResult:
        question = context.question or ""
        if any(term in question.casefold() for term in _MEDICAL_TERMS):
            message = (
                "This is a simulated Nutri-Box coaching response. Nutri-Box cannot diagnose "
                "conditions or provide medical treatment; please consult a qualified healthcare professional."
            )
        else:
            message = "This is a simulated Nutri-Box coaching response."

        highlights = [self._meal_highlight(context.today.meal_count)]
        highlights.append(
            "Configured nutrition targets are available for neutral comparison."
            if context.target is not None
            else "No configured nutrition targets are currently available."
        )
        if context.profile and (context.profile.dietary_restrictions or context.profile.allergies):
            highlights.append(
                "Configured dietary restrictions and allergies are included in the simulated context."
            )
        if context.question:
            highlights.append("Your optional question is included in this simulated response context.")
        return NutritionCoachResult(message=message, highlights=tuple(highlights), provider="mock")

    async def generate_chat_reply(self, context: NutritionCoachContext) -> NutritionCoachResult:
        return NutritionCoachResult(
            message="This is a simulated Nutri-Box chat response.",
            highlights=(),
            provider="mock",
        )

    @staticmethod
    def _meal_highlight(meal_count: int) -> str:
        if meal_count == 0:
            return "Nutri-Box has no recorded meal data for the selected day."
        return f"{meal_count} meal(s) are currently recorded for the selected day."
