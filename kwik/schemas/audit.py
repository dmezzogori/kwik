from typing import Optional

from pydantic import BaseModel

from kwik.schemas.mixins.orm import ORMMixin


class _BaseSchema(BaseModel):
    client_host: str
    request_id: Optional[str] = None
    user_id: Optional[int] = None
    impersonator_user_id: Optional[int] = None
    method: str
    headers: str
    url: str
    query_params: Optional[str] = None
    path_params: Optional[str] = None
    body: Optional[str] = None
    process_time: Optional[str] = None
    status_code: Optional[str] = None


class AuditBaseSchema(ORMMixin, _BaseSchema):
    pass


class AuditCreateSchema(_BaseSchema):
    pass
