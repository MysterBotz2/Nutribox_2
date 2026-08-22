from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SensitiveProfileContext(Base):
    """Voluntary sensitive declarations, isolated from the ordinary profile."""

    __tablename__ = "sensitive_profile_contexts"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(medical_conditions) = 'array'", name="ck_sensitive_context_medical_conditions_array"),
        CheckConstraint("jsonb_typeof(medical_needs) = 'array'", name="ck_sensitive_context_medical_needs_array"),
        CheckConstraint(
            "pregnancy_status IS NULL OR pregnancy_status IN ('pregnant', 'postpartum', 'none', 'declined')",
            name="ck_sensitive_context_pregnancy_status",
        ),
        CheckConstraint(
            "pregnancy_duration_unit IS NULL OR pregnancy_duration_unit IN ('weeks', 'months')",
            name="ck_sensitive_context_pregnancy_duration_unit",
        ),
        CheckConstraint(
            "pregnancy_duration_value IS NULL OR pregnancy_duration_value BETWEEN 0 AND 1000",
            name="ck_sensitive_context_pregnancy_duration_value",
        ),
        CheckConstraint(
            "smoking_status IS NULL OR smoking_status IN ('never', 'last_6_months', 'last_12_months', 'more_than_12_months_ago')",
            name="ck_sensitive_context_smoking_status",
        ),
        CheckConstraint(
            "smoking_method IS NULL OR smoking_method IN ('cigarettes', 'alternative_tobacco', 'vaping', 'e_cigarettes', 'cannabis', 'none')",
            name="ck_sensitive_context_smoking_method",
        ),
        CheckConstraint(
            "drinking_status IS NULL OR drinking_status IN ('never', 'former', 'current')",
            name="ck_sensitive_context_drinking_status",
        ),
        CheckConstraint(
            "drinking_frequency IS NULL OR drinking_frequency IN ('daily', 'weekly', 'monthly', 'occasionally', 'rarely')",
            name="ck_sensitive_context_drinking_frequency",
        ),
        CheckConstraint(
            "drinking_average_intake IS NULL OR drinking_average_intake IN ('one_to_two', 'three_to_four', 'five_or_more')",
            name="ck_sensitive_context_drinking_average_intake",
        ),
        CheckConstraint(
            "last_alcohol_consumption IS NULL OR last_alcohol_consumption IN ('last_24_hours', 'last_7_days', 'last_30_days', 'more_than_30_days_ago', 'never')",
            name="ck_sensitive_context_last_alcohol_consumption",
        ),
        CheckConstraint(
            "alcohol_type IS NULL OR alcohol_type IN ('beer', 'wine', 'spirits', 'mixed_drinks')",
            name="ck_sensitive_context_alcohol_type",
        ),
        CheckConstraint(
            "body_build IS NULL OR body_build IN ('lean', 'average', 'muscular', 'stocky')",
            name="ck_sensitive_context_body_build",
        ),
        CheckConstraint(
            "ethnicity IS NULL OR ethnicity IN ('filipino', 'other', 'declined')",
            name="ck_sensitive_context_ethnicity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    medical_conditions: Mapped[list[str] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    medical_conditions_other: Mapped[str | None] = mapped_column(String(250), nullable=True)
    pregnancy_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pregnancy_duration_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pregnancy_duration_unit: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pregnancy_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    smoking_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    smoking_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    drinking_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    drinking_frequency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    drinking_average_intake: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_alcohol_consumption: Mapped[str | None] = mapped_column(String(32), nullable=True)
    alcohol_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    body_build: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    medical_needs: Mapped[list[str] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="sensitive_profile_context")
