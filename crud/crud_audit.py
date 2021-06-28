from typing import Optional, Any

from .base import CRUDBase

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app import kwik
from app.kwik.models.audit import Audit
from app.kwik.schemas import AuditCreateSchema, AuditUpdateSchema


class CRUDAudit(CRUDBase[Audit, AuditCreateSchema, AuditUpdateSchema]):
    def create(
            self,
            *,
            db: Session,
            request: Request,
            body: Any,
            response: Response,
            process_time: float,
            user_id: Optional[int] = None,
            impersonator_user_id: Optional[int] = None) -> Audit:
        audit_db = Audit(
            client_host=request.client.host,
            request_id=kwik.middlewares.get_request_id(),
            user_id=user_id,
            impersonator_user_id=impersonator_user_id,
            method=request.method,
            headers=repr(request.headers),
            url=request.url.path,
            query_params=repr(request.query_params),
            path_params=repr(request.path_params),
            body=str(body),
            process_time=process_time * 1000,
            status_code=response.status_code
        )
        db.add(audit_db)
        db.flush()
        db.refresh(audit_db)
        return audit_db


audit = CRUDAudit(Audit)
