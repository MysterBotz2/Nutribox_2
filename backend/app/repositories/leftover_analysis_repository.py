from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.leftover_analysis import LeftoverAnalysis
class LeftoverAnalysisRepository:
 def __init__(self,session:Session): self.session=session
 def add(self,analysis:LeftoverAnalysis): self.session.add(analysis)
 def get_by_meal_id(self,meal_id:int): return self.session.scalar(select(LeftoverAnalysis).where(LeftoverAnalysis.meal_id==meal_id))
