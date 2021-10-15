from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from kwik import models, schemas
from .base import CRUDBase


class CRUDLogs(CRUDBase[models.Log, schemas.LogCreateSchema, schemas.LogUpdateSchema]):
    def create(self, *, db: Session, obj_in: schemas.LogCreateSchema) -> models.Log:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)


logs = CRUDLogs(models.Log)
