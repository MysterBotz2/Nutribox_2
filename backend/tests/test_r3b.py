from datetime import datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.meal import Meal
from app.models.scheduled_meal import ScheduledMeal
from conftest import register_and_login

def p(**x): return {"weight_kg":"70.000","measured_at":"2026-08-10T00:00:00Z",**x}
def test_weight_entries_crud_validation_and_isolation(client:TestClient,jwt_configuration):
 u,h=register_and_login(client); _,h2=register_and_login(client,"other@example.com")
 assert client.post('/api/weight-entries',json=p()).status_code==401
 r=client.post('/api/weight-entries',json=p(),headers=h); assert r.status_code==201; i=r.json()['id']
 assert client.post('/api/weight-entries',json=p(user_id=9),headers=h).status_code==422
 assert client.post('/api/weight-entries',json=p(weight_kg='0'),headers=h).status_code==422
 assert client.post('/api/weight-entries',json=p(weight_kg='501'),headers=h).status_code==422
 assert client.post('/api/weight-entries',json=p(measured_at='2026-08-10T00:00:00'),headers=h).status_code==422
 assert client.get(f'/api/weight-entries/{i}',headers=h2).status_code==404
 assert client.put(f'/api/weight-entries/{i}',json=p(weight_kg='71'),headers=h).status_code==200
 assert client.delete(f'/api/weight-entries/{i}',headers=h2).status_code==404
 assert client.delete(f'/api/weight-entries/{i}',headers=h).status_code==204
def test_weekly_diagnostics_factual_boundaries(client:TestClient,database_session:Session,jwt_configuration):
 u,h=register_and_login(client); o,oh=register_and_login(client,'other2@example.com')
 for uid,at,c in [(u['id'],datetime(2026,8,10,tzinfo=timezone.utc),'70.000'),(u['id'],datetime(2026,8,17,tzinfo=timezone.utc),'99.000'),(o['id'],datetime(2026,8,10,tzinfo=timezone.utc),'88.000')]: database_session.add(Meal(user_id=uid,recorded_at=at,total_calories=Decimal(c),total_protein_g=Decimal('1'),total_carbohydrates_g=Decimal('2'),total_fat_g=Decimal('3'),total_fiber_g=Decimal('4')))
 database_session.add(ScheduledMeal(user_id=u['id'],scheduled_for=datetime(2026,8,10,tzinfo=timezone.utc),title='Lunch'))
 database_session.flush()
 r=client.get('/api/progress/weekly-diagnostics',params={'week_start':'2026-08-10'},headers=h); assert r.status_code==200
 d=r.json(); assert d['meals_logged']==1 and d['scheduled_meals']==1 and d['nutrition']['calories']['total']=='70.000' and d['nutrition']['calories']['daily_average']=='10.000' and d['target_comparison']['calories']['state']=='target_unavailable'
 assert client.get('/api/progress/weekly-diagnostics',params={'week_start':'2026-08-11'},headers=h).status_code==422
