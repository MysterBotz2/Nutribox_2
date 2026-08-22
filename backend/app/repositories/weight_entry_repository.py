from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.weight_entry import WeightEntry
class WeightEntryRepository:
 def __init__(self,session:Session): self.session=session
 def get(self,id:int,user:int): return self.session.scalar(select(WeightEntry).where(WeightEntry.id==id,WeightEntry.user_id==user))
 def list(self,user:int,limit:int,offset:int,start:datetime|None=None,end:datetime|None=None):
  s=select(WeightEntry).where(WeightEntry.user_id==user)
  if start:s=s.where(WeightEntry.measured_at>=start)
  if end:s=s.where(WeightEntry.measured_at<=end)
  return list(self.session.scalars(s.order_by(WeightEntry.measured_at.desc(),WeightEntry.id.desc()).limit(limit).offset(offset)))
