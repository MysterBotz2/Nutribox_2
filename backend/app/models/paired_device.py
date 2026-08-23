from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PairedDevice(Base):
    __tablename__ = "paired_devices"
    __table_args__ = (CheckConstraint("device_type = 'nutribox_pi'", name="ck_paired_devices_type"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="nutribox_pi")
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    paired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user: Mapped["User"] = relationship(back_populates="paired_devices")


class DevicePairingSession(Base):
    __tablename__ = "device_pairing_sessions"
    __table_args__ = (CheckConstraint("device_type = 'nutribox_pi'", name="ck_pairing_sessions_type"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pairing_code_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    device_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    device_name: Mapped[str] = mapped_column(String(160), nullable=False)
    device_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="nutribox_pi")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paired_device_id: Mapped[int | None] = mapped_column(ForeignKey("paired_devices.id", ondelete="SET NULL"), nullable=True, unique=True)
