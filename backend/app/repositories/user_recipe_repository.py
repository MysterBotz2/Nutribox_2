from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user_recipe import UserRecipe


class UserRecipeRepository:
    """Persistence operations for owner-scoped personal recipe records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, recipe: UserRecipe) -> UserRecipe:
        """Add a recipe and its attached ingredients in the caller's transaction."""
        self.session.add(recipe)
        self.session.flush()
        return recipe

    def get_by_id_for_user(self, recipe_id: int, user_id: int) -> UserRecipe | None:
        statement = (
            select(UserRecipe)
            .options(selectinload(UserRecipe.ingredients))
            .where(UserRecipe.id == recipe_id, UserRecipe.user_id == user_id)
        )
        return self.session.scalar(statement)

    def list_for_user(self, user_id: int) -> list[UserRecipe]:
        statement = (
            select(UserRecipe)
            .options(selectinload(UserRecipe.ingredients))
            .where(UserRecipe.user_id == user_id)
            .order_by(UserRecipe.updated_at.desc(), UserRecipe.id.desc())
        )
        return list(self.session.scalars(statement))

    def find_by_normalized_name_for_user(
        self, user_id: int, normalized_name: str
    ) -> list[UserRecipe]:
        statement = (
            select(UserRecipe)
            .options(selectinload(UserRecipe.ingredients))
            .where(
                UserRecipe.user_id == user_id,
                UserRecipe.normalized_name == normalized_name,
            )
            .order_by(UserRecipe.updated_at.desc(), UserRecipe.id.desc())
        )
        return list(self.session.scalars(statement))

    def delete_for_user(self, recipe_id: int, user_id: int) -> bool:
        recipe = self.get_by_id_for_user(recipe_id, user_id)
        if recipe is None:
            return False

        self.session.delete(recipe)
        return True
