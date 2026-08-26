from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.repositories.user_recipe_repository import UserRecipeRepository
from app.services.meal_analysis_session_service import MealAnalysisSessionService
from app.services.user_recipe_service import UserRecipeService


def get_user_recipe_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> UserRecipeService:
    return UserRecipeService(
        UserRecipeRepository(database_session),
        MealAnalysisSessionService(MealAnalysisSessionRepository(database_session)),
    )
