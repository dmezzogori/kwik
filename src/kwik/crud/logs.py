"""CRUD operations for logs database entities."""

from typing import Never

from fastapi.encoders import jsonable_encoder

from kwik import models
from kwik.models import User
from kwik.schemas import LogCreateSchema

from .base import CRUDBase


class CRUDLogs(CRUDBase):
    """CRUD operations for application log entries with user tracking."""

    def create(self, *, obj_in: LogCreateSchema, user: User | None = None) -> models.Log:
        """Create new log entry with optional user association."""
        obj_in_data = jsonable_encoder(obj_in)
        if user is not None:
            db_obj: models.Log = self.model(**obj_in_data, creator_user_id=user.id)
        else:
            db_obj: models.Log = self.model(**obj_in_data)
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def create_if_not_exist(self, *args, **kwargs) -> Never:
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError

    def get(self, *, id: int) -> Never:  # noqa: A002
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError

    def get_all(self) -> Never:
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError

    def get_multi(self, *, skip: int = 0, limit: int = 100, sort=None, **filters) -> Never:
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError

    def get_if_exist(self, *, id: int) -> Never:  # noqa: A002
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError

    def update(self, *, db_obj, obj_in) -> Never:
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError

    def delete(self, *, id: int) -> Never:  # noqa: A002
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError


logs = CRUDLogs(models.Log)
