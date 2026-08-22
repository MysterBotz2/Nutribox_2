from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProfileConsent(Base):
    """Purpose-specific product consent owned by one user.

    This stores application permission states only; it is not a legal-consent ledger.
    """

    __tablename__ = "profile_consents"
    __table_args__ = (
        CheckConstraint(
            "sensitive_storage IN ('not_asked', 'granted', 'declined', 'withdrawn')",
            name="ck_profile_consents_sensitive_storage",
        ),
        CheckConstraint(
            "personalization IN ('not_asked', 'granted', 'declined', 'withdrawn')",
            name="ck_profile_consents_personalization",
        ),
        CheckConstraint(
            "ai_context IN ('not_asked', 'granted', 'declined', 'withdrawn')",
            name="ck_profile_consents_ai_context",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    sensitive_storage: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="not_asked"
    )
    personalization: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="not_asked"
    )
    ai_context: Mapped[str] = mapped_column(String(16), nullable=False, server_default="not_asked")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile_consent")
