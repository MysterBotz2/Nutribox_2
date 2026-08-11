from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.food import Food
from app.models.food_alias import FoodAlias


class FoodRepository:
    """Database operations for canonical food reference records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, food_id: int) -> Food | None:
        return self._session.get(Food, food_id)

    def get_by_normalized_name(self, normalized_name: str) -> Food | None:
        statement = select(Food).where(Food.normalized_name == normalized_name)
        return self._session.scalar(statement)

    def search(self, query: str) -> list[Food]:
        pattern = f"%{query}%"
        statement = (
            select(Food)
            .outerjoin(FoodAlias, FoodAlias.food_id == Food.id)
            .where(
                or_(
                    Food.name.ilike(pattern),
                    Food.normalized_name.ilike(pattern),
                    FoodAlias.alias.ilike(pattern),
                    FoodAlias.normalized_alias.ilike(pattern),
                )
            )
            .distinct()
            .order_by(Food.name)
        )
        return list(self._session.scalars(statement))
