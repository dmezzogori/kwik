from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import kwik
from app.kwik import schemas
from app.kwik.core.config import settings
from app.kwik.db.base_class import Base, SoftDeleteMixin
from app.kwik.typings import ParsedSortingQuery

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(self, *, db: Session, id: Any) -> Optional[ModelType]:
        if issubclass(self.model, SoftDeleteMixin):
            return db.query(self.model).filter(self.model.id == id, self.model.deleted == False).first()
        else:
            return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, *, db: Session, skip: int = 0, limit: int = 100, sort: ParsedSortingQuery = None, **filters
    ) -> Tuple[int, List[ModelType]]:
        q = db.query(self.model)
        if filters:
            q = q.filter_by(**filters)
        if issubclass(self.model, SoftDeleteMixin):
            q = q.filter(self.model.deleted == False)
        count = q.count()

        if sort is not None:
            q = kwik.utils.sort_query(model=self.model, query=q, sort=sort)

        return count, q.offset(skip).limit(limit).all()

    def create(self, *, db: Session, obj_in: CreateSchemaType, user: Optional[Any] = None) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        if user is not None:
            db_obj = self.model(**obj_in_data, creator_user_id=user.id)
        else:
            db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = schemas.LogCreateSchema(
                request_id=kwik.middlewares.get_request_id(),
                entity=db_obj.__tablename__,
                before=None,
                after=jsonable_encoder(db_obj),
            )
            kwik.crud.logs.create(db=db, obj_in=log_in)

        return db_obj

    def create_if_not_exist(
        self, *, db: Session, obj_in: CreateSchemaType, user: Optional[Any] = None, **kwargs
    ) -> ModelType:
        obj_db = db.query(self.model).filter_by(**kwargs).one_or_none()
        if obj_db is None:
            obj_db = self.create(db=db, obj_in=obj_in, user=user)
        return obj_db

    def update(
        self,
        *,
        db: Session,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        user: Optional[Any] = None
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        if user is not None:
            update_data["last_modifier_user_id"] = user.id

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)

        if settings.DB_LOGGER:
            log_in = schemas.LogCreateSchema(
                request_id=kwik.middlewares.get_request_id(),
                entity=db_obj.__tablename__,
                before=obj_data,
                after=jsonable_encoder(db_obj),
            )
            kwik.crud.logs.create(db=db, obj_in=log_in)

        return db_obj

    def remove(self, *, db: Session, id: int, user: Optional[Any] = None) -> ModelType:
        obj = db.query(self.model).get(id)

        if settings.DB_LOGGER:
            log_in = schemas.LogCreateSchema(
                request_id=kwik.middlewares.get_request_id(),
                entity=obj.__tablename__,
                before=jsonable_encoder(obj),
                after=None,
            )
            kwik.crud.logs.create(db=db, obj_in=log_in)

        if issubclass(self.model, SoftDeleteMixin):
            # TODO: portare a livello globale
            obj.deleted = True
            obj.last_modifier_user_id = user.id
        else:
            db.delete(obj)
        db.flush()
        return obj
