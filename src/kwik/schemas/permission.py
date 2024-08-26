from __future__ import annotations

from kwik.schemas.mixins.orm import ORMMixin
from pydantic import BaseModel


class _BaseSchema(BaseModel):
    name: str


class PermissionORMSchema(ORMMixin, _BaseSchema):
    pass


class PermissionCreate(_BaseSchema):
    pass


class PermissionUpdate(_BaseSchema):
    pass
