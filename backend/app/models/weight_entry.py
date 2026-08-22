from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class WeightEntry(Base):
    __tablename__ = "weight_entries"
    __table_args__ = (Index("ix_weight_entries_user_id_measured_at", "user_id", "measured_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user: Mapped["User"] = relationship(back_populates="weight_entries")
