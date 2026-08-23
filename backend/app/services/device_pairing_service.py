import hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone

from app.models.paired_device import DevicePairingSession, PairedDevice
from app.repositories.device_pairing_repository import DevicePairingRepository

class PairingError(ValueError): pass

class DevicePairingService:
    def __init__(self, repository: DevicePairingRepository, secret: str, ttl_seconds: int): self._repo=repository; self._secret=secret.encode(); self._ttl=ttl_seconds
    def start(self, name: str):
        for _ in range(10):
            code=f"{secrets.randbelow(1_000_000):06d}"; digest=self._code_digest(code)
            if self._repo.get_session_by_code(digest) is None: break
        else: raise PairingError("Pairing could not be started.")
        token=secrets.token_urlsafe(32); now=datetime.now(timezone.utc)
        session=DevicePairingSession(id=secrets.token_urlsafe(24), pairing_code_digest=digest, device_token_hash=self._token_hash(token), device_name=name, expires_at=now+timedelta(seconds=self._ttl))
        self._repo.add(session); self._repo.session.flush(); return session, code, token
    def status(self, session_id: str, token: str):
        session=self._repo.get_session(session_id)
        if session is None or not hmac.compare_digest(session.device_token_hash, self._token_hash(token)): raise PairingError("Pairing session was not found.")
        if session.paired_at is not None: return "paired", session.paired_device_id
        if session.expires_at <= datetime.now(timezone.utc): return "expired", None
        return "pending", None
    def claim(self, user_id: int, code: str):
        session=self._repo.get_session_by_code(self._code_digest(code))
        if session is None or session.paired_at is not None or session.expires_at <= datetime.now(timezone.utc): raise PairingError("Pairing code is invalid or expired.")
        device=PairedDevice(user_id=user_id, name=session.device_name, device_type=session.device_type, token_hash=session.device_token_hash)
        self._repo.add(device); self._repo.session.flush(); session.paired_at=datetime.now(timezone.utc); session.paired_device_id=device.id; self._repo.session.flush(); return device
    def revoke(self, device): device.revoked_at=datetime.now(timezone.utc); self._repo.session.flush()
    def authenticated_device(self, token: str):
        device=self._repo.get_device_by_token(self._token_hash(token))
        return device if device is not None and device.revoked_at is None else None
    def _code_digest(self, code: str): return hmac.new(self._secret, code.encode(), hashlib.sha256).hexdigest()
    @staticmethod
    def _token_hash(token: str): return hashlib.sha256(token.encode()).hexdigest()
