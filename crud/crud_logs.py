from typing import Optional, Dict

from sqlalchemy.orm import Session

from app import kwik
from app.kwik.models.logger import Log
from app.kwik.schemas import LogCreateSchema, LogUpdateSchema
from .base import CRUDBase


class CRUDLogs(CRUDBase[Log, LogCreateSchema, LogUpdateSchema]):
    def create(
            self,
            *,
            db: Session,
            entity: str,
            before: Optional[Dict] = None,
            after: Dict
    ) -> Log:
        log_db = Log(
            request_id=kwik.middlewares.get_request_id(),
            entity=entity,
            before=before,
            after=after
        )
        db.add(log_db)
        db.flush()
        db.refresh(log_db)
        return log_db


logs = CRUDLogs(Log)
