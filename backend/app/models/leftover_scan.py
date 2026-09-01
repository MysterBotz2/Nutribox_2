from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class LeftoverScan(Base):
    """Immutable account-linked result of consuming a completed leftover analysis session."""

    __tablename__ = "leftover_scans"
    __table_args__ = (
        UniqueConstraint("analysis_session_id", name="uq_leftover_scans_analysis_session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_session_id: Mapped[int] = mapped_column(
        ForeignKey("meal_analysis_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    original_weight_grams: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    remaining_weight_grams: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    consumed_weight_grams: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    consumed_portion_percentage: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    remaining_nutrition_snapshot: Mapped[dict] = mapped_column(JSONB(none_as_null=True), nullable=False)
    consumed_nutrition_snapshot: Mapped[dict] = mapped_column(JSONB(none_as_null=True), nullable=False)
    comparison_warnings: Mapped[list] = mapped_column(JSONB(none_as_null=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    meal: Mapped["Meal"] = relationship(back_populates="leftover_scans")
