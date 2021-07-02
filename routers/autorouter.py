from __future__ import annotations

import inspect
from typing import Any, Generic, List, Optional, Type

from sqlalchemy.orm import Session

from app import kwik
from app.kwik.typings import ModelType, BaseSchemaType, CreateSchemaType, UpdateSchemaType, SortingQuery
from .auditor import AuditorRouter


class AutoRouter(Generic[ModelType, BaseSchemaType, CreateSchemaType, UpdateSchemaType]):
    def __init__(
        self, model: Type[ModelType], schemas, crud, *args, permissions: Optional[List[str]] = None, **kwargs,
    ):

        super().__init__(*args, **kwargs)
        self.model = model
        self.BaseSchemaType, self.CreateSchemaType, self.UpdateSchemaType = schemas
        self.crud = crud
        self.permissions = permissions
        self.deps = [kwik.current_user]

        if permissions is not None:
            self.deps.append(kwik.has_permission(*permissions))

        self.router = AuditorRouter()

        self.register()

    def __init_subclass__(cls):
        base = cls.__orig_bases__[0]
        Model, BaseSchema, CreateSchema, UpdateSchema = base.__args__

        def modify_create_signature():
            async def new_create(*args, **kwargs):
                return base.create(*args, **kwargs)

            create = base.create
            annotations = create.__annotations__.copy()
            annotations["obj_in"] = CreateSchema
            new_create.__annotations__ = annotations

            base_sign = inspect.signature(base.create)
            params = []
            for param_name, param in base_sign.parameters.items():
                if param_name == "obj_in":
                    params.append(inspect.Parameter(param_name, param.kind, annotation=CreateSchema))
                else:
                    params.append(param)
            new_create.__signature__ = inspect.Signature(params)
            cls.create = new_create

        def modify_update_sign():
            async def new_update(*args, **kwargs):
                await base.update(*args, **kwargs)

            update = base.update
            annotations = update.__annotations__.copy()
            annotations["obj_in"] = UpdateSchema
            new_update.__annotations__ = annotations

            base_sign = inspect.signature(base.update)
            params = []
            for param_name, param in base_sign.parameters.items():
                if param_name == "obj_in":
                    params.append(inspect.Parameter(param_name, param.kind, annotation=UpdateSchema))
                else:
                    params.append(param)
            new_update.__signature__ = inspect.Signature(params)
            cls.update = new_update

        if getattr(cls, "create") == getattr(base, "create"):
            modify_create_signature()

        if getattr(cls, "update") == getattr(base, "update"):
            modify_update_sign()

    @property
    def name(self) -> str:
        return self.model.__tablename__

    def read_multi(
        self,
        db: Session = kwik.db,
        filters: kwik.typings.FilterQuery = kwik.FilterQuery,
        sorting: kwik.typings.ParsedSortingQuery = kwik.SortingQuery,
        paginated: kwik.typings.PaginatedQuery = kwik.PaginatedQuery,
    ) -> kwik.schemas.Paginated[BaseSchemaType]:
        """
        Retrieve many {name} items.
        Sorting field:[asc|desc]
        """
        total, result = self.crud.get_multi(db=db, **filters, sort=sorting, **paginated)
        return kwik.schemas.Paginated[self.BaseSchemaType](total=total, data=result)

    def read(self, id: int, db: Session = kwik.db) -> ModelType:
        """
        Retrieve a {name}.
        """
        db_obj = self.crud.get(db=db, id=id)
        if not db_obj:
            raise kwik.exceptions.NotFound(id=id)
        return db_obj

    def create(
        self, *, db: Session = kwik.db, obj_in: CreateSchemaType, user: kwik.models.User = kwik.current_user
    ) -> Any:
        """
        Create a {name}.
        """
        obj_db = self.crud.create(db=db, obj_in=obj_in, user=user)
        return obj_db

    def update(
        self, *, db: Session = kwik.db, id: int, obj_in: UpdateSchemaType, user: kwik.models.User = kwik.current_user
    ) -> Any:
        """
        Update a {name}.
        """
        db_obj = self.crud.get(db=db, id=id)
        if not db_obj:
            raise kwik.exceptions.NotFound(id=id)
        return self.crud.update(db=db, db_obj=db_obj, obj_in=obj_in, user=user)

    def remove(self, *, db: Session = kwik.db, id: int,) -> Any:
        """
        Delete a {name}.
        """
        obj_db = self.crud.get(db=db, id=id)
        if not obj_db:
            raise kwik.exceptions.NotFound(id=id)
        return self.crud.remove(db=db, id=id)

    def register(self, *, read_multi=True, read=True, create=True, update=True, delete=True):
        if read_multi:
            self.router.get("/", response_model=kwik.schemas.Paginated[self.BaseSchemaType], dependencies=self.deps)(
                self.read_multi
            )
        if read:
            self.router.get("/{id}", response_model=self.BaseSchemaType, dependencies=self.deps)(self.read)
        if create:
            self.router.post("/", response_model=self.BaseSchemaType, dependencies=self.deps)(self.create)
        if update:
            self.router.put("/{id}", response_model=self.BaseSchemaType, dependencies=self.deps)(self.update)
        if delete:
            self.router.delete("/{id}", dependencies=self.deps)(self.remove)
