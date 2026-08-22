from datetime import datetime
from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException,Query,Response,status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.weight_entry import WeightEntry
from app.repositories.weight_entry_repository import WeightEntryRepository
from app.schemas.weight_entry import WeightEntryList,WeightEntryResponse,WeightEntryWrite
router=APIRouter(prefix="/api/weight-entries",tags=["weight entries"])
def repo(db:Annotated[Session,Depends(get_db)]): return WeightEntryRepository(db)
def window(a,b):
 if any(x and (x.tzinfo is None or x.utcoffset() is None) for x in (a,b)) or (a and b and a>b): raise HTTPException(422,"Weight-entry window timestamps must include offsets and be ordered.")
@router.post("",response_model=WeightEntryResponse,status_code=201)
def create(r:WeightEntryWrite,u:Annotated[User,Depends(get_current_user)],p:Annotated[WeightEntryRepository,Depends(repo)]):
 e=WeightEntry(user_id=u.id,**r.model_dump());p.session.add(e);p.session.flush();return e
@router.get("",response_model=WeightEntryList)
def list_entries(u:Annotated[User,Depends(get_current_user)],p:Annotated[WeightEntryRepository,Depends(repo)],measured_from:datetime|None=Query(None),measured_to:datetime|None=Query(None),limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
 window(measured_from,measured_to);return WeightEntryList(entries=p.list(u.id,limit,offset,measured_from,measured_to),limit=limit,offset=offset)
@router.get("/{entry_id}",response_model=WeightEntryResponse)
def get(entry_id:int,u:Annotated[User,Depends(get_current_user)],p:Annotated[WeightEntryRepository,Depends(repo)]):
 e=p.get(entry_id,u.id)
 if not e: raise HTTPException(404,"Weight entry was not found.")
 return e
@router.put("/{entry_id}",response_model=WeightEntryResponse)
def update(entry_id:int,r:WeightEntryWrite,u:Annotated[User,Depends(get_current_user)],p:Annotated[WeightEntryRepository,Depends(repo)]):
 e=get(entry_id,u,p);e.weight_kg=r.weight_kg;e.measured_at=r.measured_at;p.session.flush();return e
@router.delete("/{entry_id}",status_code=204)
def delete(entry_id:int,u:Annotated[User,Depends(get_current_user)],p:Annotated[WeightEntryRepository,Depends(repo)]): p.session.delete(get(entry_id,u,p));p.session.flush();return Response(status_code=204)
