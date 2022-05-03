from typing import Optional, Any

from pydantic import BaseModel

from kwik.schemas.mixins.orm import ORMMixin


class _BaseSchema(BaseModel):
    request_id: Optional[str] = None
    entity: Optional[str] = None
    before: Optional[Any] = None
    after: Optional[Any] = None


class LogORMSchema(ORMMixin, _BaseSchema):
    pass


class LogCreateSchema(_BaseSchema):
    pass
