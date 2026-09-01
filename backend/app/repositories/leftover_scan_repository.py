from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.leftover_scan import LeftoverScan


class LeftoverScanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, scan: LeftoverScan) -> None:
        self.session.add(scan)

    def get_by_analysis_session_id(self, analysis_session_id: int) -> LeftoverScan | None:
        return self.session.scalar(
            select(LeftoverScan).where(LeftoverScan.analysis_session_id == analysis_session_id)
        )
