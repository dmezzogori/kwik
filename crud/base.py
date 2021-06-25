from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, Tuple

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.kwik.core.config import settings
from app.kwik.db.base_class import Base
from app.kwik.models import Logging

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


def log(db: Session, entity: str, before: dict, after: dict):
    log_db = Logging(
        entity=entity,
        before=before,
        after=after
    )
    db.add(log_db)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, sort: Optional[List[Tuple[str, str]]] = None, **kwargs
    ) -> Tuple[int, List[ModelType]]:
        q = db.query(self.model)
        if kwargs:
            q = q.filter_by(**kwargs)
        count = q.count()

        if sort is not None:
            order_by = []
            for attr, order in sort:
                model_attr = getattr(self.model, attr)
                if order == 'asc':
                    order_by.append(model_attr.asc())
                else:
                    order_by.append(model_attr.desc())
            q = q.order_by(*order_by)
        return count, q.offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        if settings.DB_LOGGER:
            log(db=db, entity=db_obj.__tablename__, before=obj_data, after=jsonable_encoder(db_obj))

        return db_obj

    def remove(self, db: Session, *, id: int) -> ModelType:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.flush()
        return obj
