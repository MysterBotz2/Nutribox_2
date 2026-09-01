"""Central SQLAlchemy model registry.

Import this package before standalone ORM work so every string-based
relationship target is registered with ``Base``.
"""

from app.models.chat import ChatConversation, ChatMessage
from app.models.food import Food
from app.models.food_alias import FoodAlias
from app.models.leftover_analysis import LeftoverAnalysis
from app.models.leftover_scan import LeftoverScan
from app.models.meal import Meal, MealItem
from app.models.meal_analysis_session import MealAnalysisSession
from app.models.nutrition_profile import NutritionProfile
from app.models.nutrition_target import NutritionTarget
from app.models.paired_device import PairedDevice
from app.models.profile_consent import ProfileConsent
from app.models.scheduled_meal import ScheduledMeal
from app.models.sensitive_profile_context import SensitiveProfileContext
from app.models.user import User
from app.models.user_recipe import UserRecipe, UserRecipeIngredient
from app.models.weight_entry import WeightEntry

__all__ = [
    "ChatConversation", "ChatMessage", "Food", "FoodAlias", "LeftoverAnalysis", "LeftoverScan",
    "Meal", "MealItem", "MealAnalysisSession", "NutritionProfile", "NutritionTarget", "PairedDevice",
    "ProfileConsent", "ScheduledMeal", "SensitiveProfileContext", "User", "UserRecipe",
    "UserRecipeIngredient", "WeightEntry",
]
