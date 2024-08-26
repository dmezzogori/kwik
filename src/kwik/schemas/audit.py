from kwik.schemas.mixins.orm import ORMMixin
from pydantic import BaseModel


class _BaseSchema(BaseModel):
    client_host: str
    request_id: str | None = None
    user_id: int | None = None
    impersonator_user_id: int | None = None
    method: str
    headers: str
    url: str
    query_params: str | None = None
    path_params: str | None = None
    body: str | None = None
    process_time: str | None = None
    status_code: str | None = None


class AuditORMSchema(ORMMixin, _BaseSchema):
    pass


class AuditCreateSchema(_BaseSchema):
    pass
