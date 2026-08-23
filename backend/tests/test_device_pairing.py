from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.paired_device import DevicePairingSession
from conftest import register_and_login

def _start(client: TestClient):
    response=client.post('/api/device-pairing/start',json={'device_name':'Test Pi'})
    assert response.status_code==201
    return response.json()

def test_pairing_lifecycle_and_owner_isolation(client: TestClient, database_session: Session, jwt_configuration: None, monkeypatch):
    monkeypatch.setattr(settings,'device_pairing_secret','test-pairing-secret')
    started=_start(client)
    assert started['pairing_code'].isdigit() and len(started['pairing_code'])==6
    stored=database_session.get(DevicePairingSession,started['session_id'])
    assert started['pairing_code'] not in stored.pairing_code_digest and started['device_token'] not in stored.device_token_hash
    assert client.post('/api/device-pairing/status',json={'session_id':started['session_id'],'device_token':started['device_token']}).json()['status']=='pending'
    assert client.get('/api/device/me',headers={'X-Device-Token':started['device_token']}).status_code==401
    _, owner=register_and_login(client,'pair-owner@example.com')
    _, other=register_and_login(client,'pair-other@example.com')
    claimed=client.post('/api/users/me/devices/pair',json={'pairing_code':started['pairing_code']},headers=owner)
    assert claimed.status_code==201
    device_id=claimed.json()['id']
    assert client.post('/api/users/me/devices/pair',json={'pairing_code':started['pairing_code']},headers=other).status_code==422
    assert client.post('/api/device-pairing/status',json={'session_id':started['session_id'],'device_token':started['device_token']}).json()['status']=='paired'
    assert client.get('/api/device/me',headers={'X-Device-Token':started['device_token']}).status_code==200
    assert len(client.get('/api/users/me/devices',headers=owner).json()['devices'])==1
    assert client.get('/api/users/me/devices',headers=other).json()['devices']==[]
    assert client.delete(f'/api/users/me/devices/{device_id}',headers=other).status_code==404
    assert client.delete(f'/api/users/me/devices/{device_id}',headers=owner).status_code==204
    assert client.get('/api/device/me',headers={'X-Device-Token':started['device_token']}).status_code==401

def test_pairing_expiry_and_invalid_code(client: TestClient, database_session: Session, jwt_configuration: None, monkeypatch):
    monkeypatch.setattr(settings,'device_pairing_secret','test-pairing-secret')
    started=_start(client); session=database_session.get(DevicePairingSession,started['session_id']); session.expires_at -= timedelta(minutes=10); database_session.flush()
    _, headers=register_and_login(client,'pair-expired@example.com')
    assert client.post('/api/users/me/devices/pair',json={'pairing_code':started['pairing_code']},headers=headers).status_code==422
    assert client.post('/api/users/me/devices/pair',json={'pairing_code':'000000'},headers=headers).status_code==422
