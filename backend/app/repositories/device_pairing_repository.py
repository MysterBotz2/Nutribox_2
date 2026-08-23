from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.paired_device import DevicePairingSession, PairedDevice

class DevicePairingRepository:
    def __init__(self, session: Session): self.session = session
    def add(self, value): self.session.add(value)
    def get_session(self, session_id: str): return self.session.get(DevicePairingSession, session_id)
    def get_session_by_code(self, digest: str): return self.session.scalar(select(DevicePairingSession).where(DevicePairingSession.pairing_code_digest == digest))
    def get_device_by_token(self, token_hash: str): return self.session.scalar(select(PairedDevice).where(PairedDevice.token_hash == token_hash))
    def get_device_for_user(self, device_id: int, user_id: int): return self.session.scalar(select(PairedDevice).where(PairedDevice.id == device_id, PairedDevice.user_id == user_id))
    def list_for_user(self, user_id: int): return list(self.session.scalars(select(PairedDevice).where(PairedDevice.user_id == user_id, PairedDevice.revoked_at.is_(None)).order_by(PairedDevice.id)))
