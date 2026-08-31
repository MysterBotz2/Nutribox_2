from datetime import timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.paired_device import DevicePairingSession
from app.models.food import Food
from conftest import register_and_login
from test_meal_analysis import image_bytes

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
    identity = client.get('/api/device/me',headers={'X-Device-Token':started['device_token']})
    assert identity.status_code == 200
    assert identity.json()['owner_first_name'] == 'Test'
    assert {'email', 'last_name', 'token_hash', 'pairing_code', 'device_token'} & set(identity.json()) == set()
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

def test_paired_device_can_start_owner_analysis_and_credential_ambiguity_is_rejected(client: TestClient, database_session: Session, jwt_configuration: None, monkeypatch):
    monkeypatch.setattr(settings, 'device_pairing_secret', 'test-pairing-secret')
    # Keep this authorization test independent of composite-estimator fixtures.
    database_session.add(Food(
        name='chicken adobo', normalized_name='chicken adobo', category='test',
        calories_per_100g=Decimal('150'), protein_g_per_100g=Decimal('20'),
        carbohydrates_g_per_100g=Decimal('5'), fat_g_per_100g=Decimal('6'), fiber_g_per_100g=Decimal('1'),
        source_name='test', source_type='local_database', source_reference='test:chicken-adobo', is_verified=True,
    ))
    database_session.flush()
    started = _start(client)
    owner_data, owner_headers = register_and_login(client, 'device-meal-owner@example.com')
    assert client.post('/api/users/me/devices/pair', json={'pairing_code': started['pairing_code']}, headers=owner_headers).status_code == 201
    device_headers = {'X-Device-Token': started['device_token']}
    response = client.post('/api/meals/analyze', data={'weight_grams': '120'}, files={'file': ('meal.png', image_bytes(), 'image/png')}, headers=device_headers)
    assert response.status_code == 200
    assert response.json()['analysis_session_id'] is not None
    session = database_session.get(DevicePairingSession, started['session_id'])
    assert session is not None and session.paired_device_id is not None
    from app.models.meal_analysis_session import MealAnalysisSession
    analysis_session = database_session.get(MealAnalysisSession, response.json()['analysis_session_id'])
    assert analysis_session is not None and analysis_session.user_id == owner_data['id']
    ambiguous = client.post('/api/meals/analyze', data={'weight_grams': '120'}, files={'file': ('meal.png', image_bytes(), 'image/png')}, headers={**owner_headers, **device_headers})
    assert ambiguous.status_code == 400
    assert client.post('/api/meals/analyze', data={'weight_grams': '120'}, files={'file': ('meal.png', image_bytes(), 'image/png')}, headers={'X-Device-Token': 'invalid-device-token'}).status_code == 401
