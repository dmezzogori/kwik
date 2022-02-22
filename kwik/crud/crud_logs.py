from fastapi.encoders import jsonable_encoder

from .base import CRUDCreateBase
from .. import models
from ..database.session import KwikSession
from ..models import User
from ..schemas import LogCreateSchema


class CRUDLogs(CRUDCreateBase):
    def create(self, *, db: KwikSession, obj_in: LogCreateSchema, user: User | None = None) -> models.Log:
        obj_in_data = jsonable_encoder(obj_in)
        if user is not None:
            db_obj: models.Log = self.model(**obj_in_data, creator_user_id=user.id)
        else:
            db_obj: models.Log = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        return db_obj

    def create_if_not_exist(self, *args, **kwargs):
        raise NotImplementedError()


logs = CRUDLogs(models.Log)
