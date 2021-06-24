from __future__ import annotations

import inspect
from typing import List, TypeVar, Optional, Any, Generic, Type

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import kwik
from app.kwik.schemas.synth import MyBaseModel
from app.kwik.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
BaseSchemaType = TypeVar("BaseSchemaType", bound=MyBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class AutoRouter(Generic[ModelType, BaseSchemaType, CreateSchemaType, UpdateSchemaType]):
    def __init__(
            self,
            model: Type[ModelType],
            schemas,
            crud,
            *args,
            permissions: Optional[List[str]] = None,
            **kwargs):

        super().__init__(*args, **kwargs)
        self.model = model
        self.BaseSchemaType, self.CreateSchemaType, self.UpdateSchemaType = schemas
        self.crud = crud
        self.permissions = permissions
        self.deps = [kwik.current_user]
        if permissions is not None:
            self.deps.append(kwik.has_permission(*permissions))

        self.router = APIRouter()

        self.register()

    def __init_subclass__(cls):
        base = cls.__orig_bases__[0]
        Model, BaseSchema, CreateSchema, UpdateSchema = base.__args__

        def modify_create_signature():

            async def new_create(*args, **kwargs):
                return base.create(*args, **kwargs)

            create = base.create
            annotations = create.__annotations__.copy()
            annotations['obj_in'] = CreateSchema
            new_create.__annotations__ = annotations

            base_sign = inspect.signature(base.create)
            params = []
            for param_name, param in base_sign.parameters.items():
                if param_name == 'obj_in':
                    params.append(inspect.Parameter(
                        param_name,
                        param.kind,
                        annotation=CreateSchema
                    ))
                else:
                    params.append(param)
            new_create.__signature__ = inspect.Signature(params)
            cls.create = new_create

        def modify_update_sign():

            async def new_update(*args, **kwargs):
                await base.update(*args, **kwargs)

            update = base.update
            annotations = update.__annotations__.copy()
            annotations['obj_in'] = UpdateSchema
            new_update.__annotations__ = annotations

            base_sign = inspect.signature(base.update)
            params = []
            for param_name, param in base_sign.parameters.items():
                if param_name == 'obj_in':
                    params.append(inspect.Parameter(
                        param_name,
                        param.kind,
                        annotation=UpdateSchema
                    ))
                else:
                    params.append(param)
            new_update.__signature__ = inspect.Signature(params)
            cls.update = new_update

        if getattr(cls, 'create') == getattr(base, 'create'):
            modify_create_signature()

        if getattr(cls, 'update') == getattr(base, 'update'):
            modify_update_sign()

    @property
    def name(self) -> str:
        return self.model.__tablename__

    def read_multi(
        self,
        db: Session = kwik.db,
        skip: int = 0,
        limit: int = 100,
        sorting: Optional[str] = None,
        filter: Optional[str] = None,
        value: Optional[Any] = None
    ) -> List[ModelType]:
        """
        Retrieve many {name} items.
        Sorting field:[asc|desc]
        """
        filter_d = {}
        if filter and value:
            filter_d = {filter: value}

        sort = []
        if sorting is not None:
            for elem in sorting.split(','):
                if ':' in elem:
                    attr, order = elem.split(':')
                else:
                    attr = elem
                    order = 'asc'
                sort.append((attr, order))

        _, result = self.crud.get_multi(db, skip=skip, limit=limit, sort=sort, **filter_d)
        return result

    def read(
        self,
        id: int,
        db: Session = kwik.db,
    ) -> ModelType:
        """
        Retrieve a {name}.
        """
        db_obj = self.crud.get(db, id=id)
        if not db_obj: raise kwik.exceptions.NotFound(id=id)
        return db_obj

    def create(
        self,
        *,
        db: Session = kwik.db,
        obj_in: CreateSchemaType,
    ) -> Any:
        """
        Create a {name}.
        """
        obj_db = self.crud.create(db, obj_in=obj_in)
        return obj_db

    def update(
        self,
        *,
        db: Session = kwik.db,
        id: int,
        obj_in: UpdateSchemaType,
    ) -> Any:
        """
        Update a {name}.
        """
        db_obj = self.crud.get(db, id=id)
        if not db_obj: raise kwik.exceptions.NotFound(id=id)
        return self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

    def remove(
        self,
        *,
        db: Session = kwik.db,
        id: int,
    ) -> Any:
        """
        Delete a {name}.
        """
        obj_db = self.crud.get(db=db, id=id)
        if not obj_db: raise kwik.exceptions.NotFound(id=id)
        return self.crud.remove(db=db, id=id)

    def register(self):
        self.router.get("/", response_model=List[self.BaseSchemaType], dependencies=self.deps)(self.read_multi)
        self.router.get("/{id}", response_model=self.BaseSchemaType, dependencies=self.deps)(self.read)
        self.router.post("/", response_model=self.BaseSchemaType, dependencies=self.deps)(self.create)
        self.router.put("/{id}", response_model=self.BaseSchemaType, dependencies=self.deps)(self.update)
        self.router.delete("/{id}", dependencies=self.deps)(self.remove)
