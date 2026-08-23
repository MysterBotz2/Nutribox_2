"""Create one deterministic synthetic Nutri-Box account for local UI validation."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import app.models  # Register all mapped relationship targets for standalone CLI execution.
from app.database.database import SessionLocal
from app.core.config import settings
from app.models.chat import ChatConversation, ChatMessage
from app.models.food import Food
from app.models.leftover_analysis import LeftoverAnalysis
from app.models.meal import Meal, MealItem
from app.models.nutrition_profile import NutritionProfile
from app.models.nutrition_target import NutritionTarget
from app.models.profile_consent import ProfileConsent
from app.models.scheduled_meal import ScheduledMeal
from app.models.user import User
from app.models.weight_entry import WeightEntry
from app.services.security import hash_password

DEMO_EMAIL = "demo@example.com"
DEMO_MARKER = "nutribox_demo_seed_v1"


def _food(session: Session, name: str, source_type: str, calories: str, protein: str, carbs: str, fat: str, fiber: str) -> Food:
    food = session.scalar(select(Food).where(Food.normalized_name == name.casefold()))
    if food is None:
        food = Food(name=name, category="demo", calories_per_100g=Decimal(calories), protein_g_per_100g=Decimal(protein), carbohydrates_g_per_100g=Decimal(carbs), fat_g_per_100g=Decimal(fat), fiber_g_per_100g=Decimal(fiber), source_name="Nutri-Box demo seed", source_type=source_type, source_reference=DEMO_MARKER, is_verified=True)
        session.add(food)
        session.flush()
    return food


def _meal(user: User, food: Food, recorded_at: datetime, grams: int) -> Meal:
    multiplier = Decimal(grams) / Decimal("100")
    values = {"calories": food.calories_per_100g * multiplier, "protein": food.protein_g_per_100g * multiplier, "carbs": food.carbohydrates_g_per_100g * multiplier, "fat": food.fat_g_per_100g * multiplier, "fiber": food.fiber_g_per_100g * multiplier}
    meal = Meal(user_id=user.id, recorded_at=recorded_at, total_calories=values["calories"], total_protein_g=values["protein"], total_carbohydrates_g=values["carbs"], total_fat_g=values["fat"], total_fiber_g=values["fiber"])
    meal.items.append(MealItem(food_id=food.id, weight_grams=Decimal(grams), calculated_calories=values["calories"], calculated_protein_g=values["protein"], calculated_carbohydrates_g=values["carbs"], calculated_fat_g=values["fat"], calculated_fiber_g=values["fiber"], food_name_snapshot=food.name, food_normalized_name_snapshot=food.normalized_name, nutrition_source_type=food.source_type, nutrition_source_name_snapshot=food.source_name, nutrition_source_reference_snapshot=food.source_reference, nutrition_is_estimated=False))
    return meal


def _clear_demo_data(session: Session, user: User) -> None:
    meal_ids = select(Meal.id).where(Meal.user_id == user.id)
    session.execute(delete(LeftoverAnalysis).where(LeftoverAnalysis.meal_id.in_(meal_ids)))
    session.execute(delete(MealItem).where(MealItem.meal_id.in_(meal_ids)))
    session.execute(delete(Meal).where(Meal.user_id == user.id))
    session.execute(delete(ScheduledMeal).where(ScheduledMeal.user_id == user.id))
    session.execute(delete(WeightEntry).where(WeightEntry.user_id == user.id))
    conversation_ids = select(ChatConversation.id).where(ChatConversation.user_id == user.id)
    session.execute(delete(ChatMessage).where(ChatMessage.conversation_id.in_(conversation_ids)))
    session.execute(delete(ChatConversation).where(ChatConversation.user_id == user.id))
    session.execute(delete(NutritionProfile).where(NutritionProfile.user_id == user.id))
    session.execute(delete(NutritionTarget).where(NutritionTarget.user_id == user.id))
    session.execute(delete(ProfileConsent).where(ProfileConsent.user_id == user.id))
    session.flush()


def seed_demo_user(session: Session, password: str, reset: bool = False, now: datetime | None = None) -> User:
    """Seed the sole marked demo account. Re-running without reset is a no-op."""
    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is not None and not reset:
        return user
    if user is None:
        user = User(email=DEMO_EMAIL, password_hash=hash_password(password), first_name="Demo", last_name="NutriBox")
        session.add(user); session.flush()
    else:
        _clear_demo_data(session, user)
        session.expire(user)
        session.delete(user)
        session.flush()
        user = User(email=DEMO_EMAIL, password_hash=hash_password(password), first_name="Demo", last_name="NutriBox")
        session.add(user); session.flush()
    base = (now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    user.nutrition_profile = NutritionProfile(user_id=user.id, age=30, height_cm=Decimal("168.00"), weight_kg=Decimal("67.200"), activity_level="moderately_active", nutrition_goal="general_health", dietary_restrictions=["synthetic demo"], allergies=["synthetic demo"])
    user.nutrition_target = NutritionTarget(user_id=user.id, calories=Decimal("2000"), protein_g=Decimal("100"), carbohydrates_g=Decimal("250"), fat_g=Decimal("65"), fiber_g=Decimal("25"), source_type="manual", source_reference=DEMO_MARKER, notes="Synthetic local UI data")
    user.profile_consent = ProfileConsent(user_id=user.id, sensitive_storage="declined", personalization="granted", ai_context="declined")
    local = _food(session, "Demo Vegetable Rice Bowl", "local_database", "145", "4.2", "25.0", "3.1", "2.8")
    usda = _food(session, "Demo USDA Grilled Chicken", "USDA", "165", "31.0", "0", "3.6", "0")
    meals: list[Meal] = []
    for days_ago in range(13, -1, -1):
        food = local if days_ago % 2 else usda
        meals.append(_meal(user, food, base - timedelta(days=days_ago, hours=10), 180 + (days_ago % 3) * 20))
    meals.extend([_meal(user, local, base - timedelta(hours=12), 160), _meal(user, usda, base - timedelta(hours=7), 140)])
    session.add_all(meals); session.flush()
    first = meals[0]
    first.leftover_analysis = LeftoverAnalysis(meal_id=first.id, leftover_weight_grams=Decimal("0"), leftover_calories=Decimal("0"), leftover_protein_g=Decimal("0"), leftover_carbohydrates_g=Decimal("0"), leftover_fat_g=Decimal("0"), leftover_fiber_g=Decimal("0"), consumed_calories=first.total_calories, consumed_protein_g=first.total_protein_g, consumed_carbohydrates_g=first.total_carbohydrates_g, consumed_fat_g=first.total_fat_g, consumed_fiber_g=first.total_fiber_g, source="zero_leftover", source_reference=DEMO_MARKER)
    session.add_all([ScheduledMeal(user_id=user.id, scheduled_for=base + timedelta(days=offset, hours=8), title=title, notes="Synthetic demo plan") for offset, title in ((1, "Planned breakfast"), (2, "Planned lunch"), (4, "Planned dinner"))])
    session.add_all([WeightEntry(user_id=user.id, measured_at=base - timedelta(days=days), weight_kg=Decimal("68.0") - Decimal(index) / Decimal("10")) for index, days in enumerate((49, 42, 35, 28, 21, 14, 7, 0))])
    for question, answer in (("How has my meal logging been?", "This synthetic account has meals across the recent two weeks."), ("Show my planned meals.", "The schedule entries are synthetic plans for manual UI validation.")):
        conversation = ChatConversation(user_id=user.id); session.add(conversation); session.flush()
        session.add_all([ChatMessage(conversation_id=conversation.id, role="user", content=question), ChatMessage(conversation_id=conversation.id, role="assistant", content=answer)])
    session.flush()
    return user


def main(argv: list[str] | None = None, session_factory=None) -> int:
    parser = argparse.ArgumentParser(description="Seed the deterministic local Nutri-Box demo account.")
    parser.add_argument("--reset", action="store_true", help="Replace only the marked demo account's seeded records.")
    args = parser.parse_args(argv)
    password = os.environ.get("NUTRIBOX_DEMO_PASSWORD") or settings.nutribox_demo_password
    if not password:
        print("NUTRIBOX_DEMO_PASSWORD must be set before seeding the demo account.")
        return 1
    factory = session_factory or SessionLocal
    if factory is None:
        print("DATABASE_URL must be configured before seeding the demo account.")
        return 1
    session = factory()
    try:
        user = seed_demo_user(session, password, reset=args.reset)
        session.commit()
        print(f"Demo account ready: {user.email}")
        return 0
    except Exception:
        session.rollback(); raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
