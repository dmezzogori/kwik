"""CRUD operations for logs database entities."""

from fastapi.encoders import jsonable_encoder

from .. import models
from ..models import User
from ..schemas import LogCreateSchema
from .base import CRUDCreateBase


class CRUDLogs(CRUDCreateBase):
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

    def create_if_not_exist(self, *args, **kwargs):
        """Not implemented for logs - raises NotImplementedError."""
        raise NotImplementedError


logs = CRUDLogs(models.Log)
