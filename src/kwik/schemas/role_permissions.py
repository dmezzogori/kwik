from kwik.schemas.mixins import RecordInfoMixin
from pydantic import BaseModel


class _BaseSchema(BaseModel):
    role_id: int
    permission_id: int


class RolePermissionORMSchema(_BaseSchema, RecordInfoMixin):
    pass


class RolePermissionCreate(_BaseSchema):
    pass
