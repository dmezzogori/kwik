from __future__ import annotations

import inspect
from typing import Any, Generic, Type

import kwik
import kwik.exceptions
import kwik.models
import kwik.schemas
from fastapi import Depends
from kwik.typings import ModelType, BaseSchemaType, CreateSchemaType, UpdateSchemaType

from .auditor import AuditorRouter


class AutoRouter(Generic[ModelType, BaseSchemaType, CreateSchemaType, UpdateSchemaType]):
    def __init__(
        self,
        model: Type[ModelType],
        schemas,
        crud,
        *args,
        permissions: list[str] | None = None,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)
        self.model = model
        self.BaseSchemaType, self.CreateSchemaType, self.UpdateSchemaType = schemas
        self.crud = crud
        self.permissions = permissions
        self.deps: list[Depends] = [kwik.current_user]

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
            def new_update(*args, **kwargs):
                return base.update(*args, **kwargs)

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
        filters: kwik.typings.FilterQuery = kwik.FilterQuery,
        sorting: kwik.typings.ParsedSortingQuery = kwik.SortingQuery,
        paginated: kwik.typings.PaginatedQuery = kwik.PaginatedQuery,
    ) -> kwik.schemas.Paginated[BaseSchemaType]:
        """
        Retrieve many {name} items.
        Sorting field:[asc|desc]
        """
        total, result = self.crud.get_multi(**filters, sort=sorting, **paginated)
        return kwik.schemas.Paginated[self.BaseSchemaType](total=total, data=result)

    # noinspection PyShadowingBuiltins
    def read(self, id: int) -> ModelType:
        """
        Retrieve a {name}.
        """
        try:
            db_obj = self.crud.get_if_exist(id=id)
        except kwik.exceptions.NotFound as e:
            raise e.http_exc
        return db_obj

    def create(self, *, obj_in: CreateSchemaType, user: kwik.models.User = kwik.current_user) -> ModelType:
        """
        Create a {name}.
        """
        return self.crud.create(obj_in=obj_in, user=user)

    # noinspection PyShadowingBuiltins
    def update(self, *, id: int, obj_in: UpdateSchemaType, user: kwik.models.User = kwik.current_user) -> Any:
        """
        Update a {name}.
        """
        try:
            db_obj = self.crud.get_if_exist(id=id)
        except kwik.exceptions.NotFound as e:
            raise e.http_exc
        return self.crud.update(db_obj=db_obj, obj_in=obj_in, user=user)

    # noinspection PyShadowingBuiltins
    def delete(self, *, id: int, user: kwik.models.User = kwik.current_user) -> Any:
        """
        Delete a {name}.
        """
        try:
            self.crud.get_if_exist(id=id)
        except kwik.exceptions.NotFound as e:
            raise e.http_exc
        return self.crud.delete(id=id, user=user)

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
            self.router.delete("/{id}", dependencies=self.deps)(self.delete)
