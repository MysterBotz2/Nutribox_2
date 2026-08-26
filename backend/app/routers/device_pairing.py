from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.database.database import get_db
from app.repositories.device_pairing_repository import DevicePairingRepository
from app.schemas.device_pairing import DeviceIdentityResponse, PairingStartRequest, PairingStartResponse, PairingStatusRequest, PairingStatusResponse, PairedDeviceResponse
from app.services.device_pairing_service import DevicePairingService, PairingError

pairing_router=APIRouter(prefix="/api/device-pairing", tags=["device pairing"])
device_auth_router=APIRouter(prefix="/api/device", tags=["device pairing"])

def get_pairing_service(database_session: Annotated[Session, Depends(get_db)]) -> DevicePairingService:
    if not settings.device_pairing_secret: raise HTTPException(status_code=503, detail="Device pairing is not configured.")
    return DevicePairingService(DevicePairingRepository(database_session), settings.device_pairing_secret, settings.device_pairing_ttl_seconds)

def device_response(device): return PairedDeviceResponse(id=device.id,name=device.name,device_type=device.device_type,paired_at=device.paired_at,last_seen_at=device.last_seen_at)

@pairing_router.post("/start", response_model=PairingStartResponse, status_code=201)
def start_pairing(request: PairingStartRequest, service: Annotated[DevicePairingService, Depends(get_pairing_service)]):
    session, code, token=service.start(request.device_name)
    return PairingStartResponse(session_id=session.id,pairing_code=code,device_token=token,expires_at=session.expires_at)

@pairing_router.post("/status", response_model=PairingStatusResponse)
def pairing_status(request: PairingStatusRequest, service: Annotated[DevicePairingService, Depends(get_pairing_service)]):
    try: state, device_id=service.status(request.session_id,request.device_token)
    except PairingError as error: raise HTTPException(status_code=404,detail=str(error)) from None
    return PairingStatusResponse(status=state,device_id=device_id)

def get_current_device(x_device_token: Annotated[str | None, Header()] = None, service: DevicePairingService = Depends(get_pairing_service)):
    device=service.authenticated_device(x_device_token or "")
    if device is None: raise HTTPException(status_code=401,detail="Device authentication failed.")
    return device

@device_auth_router.get("/me", response_model=DeviceIdentityResponse)
def get_device_me(device=Depends(get_current_device)):
    return DeviceIdentityResponse(**device_response(device).model_dump(), owner_first_name=device.user.first_name)
