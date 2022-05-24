from typing import Any, Callable

import kwik
from fastapi import HTTPException

from app import crud, schemas


def NotFound(id):
    return HTTPException(status_code=404, detail="The item with id={id} does not exist in the system".format(id=id))


class AutoAPI:
    def __init__(self, Model):
        self.name = Model.__tablename__
        self.Model = Model
        self.BaseSchema = getattr(schemas, f"{Model.__name__}Base")
        self.CreateSchema = getattr(schemas, f"{Model.__name__}Create")
        self.UpdateSchema = getattr(schemas, f"{Model.__name__}Update")
        self.router = kwik.routers.AuditorRouter()
        self.crud = getattr(crud, self.name)

    def register(
        self,
        api_router,
        *,
        permissions: list[str] | None = None,
        custom_get_multi: Callable | None = None,
        custom_update: Callable | None = None,
    ):
        BaseSchema = self.BaseSchema
        CreateSchema = self.CreateSchema
        UpdateSchema = self.UpdateSchema

        def read_multi(
            db: kwik.KwikSession = kwik.db,
            skip: int = 0,
            limit: int = 100,
            filter: str | None = None,
            value: Any | None = None,
        ) -> Any:
            """
            Retrieve many {name} items.
            """
            filter_d = {}
            if filter and value:
                filter_d = {filter: value}
            return self.crud.get_multi(db, skip=skip, limit=limit, **filter_d)

        read_multi.__doc__ = read_multi.__doc__.format(name=self.name)
        if custom_get_multi is not None:
            read_multi = custom_get_multi(read_multi)

        def read(id: int, db: kwik.KwikSession = kwik.db) -> Any:
            """
            Retrieve a {name}.
            """
            return self.crud.get(db, id=id)

        read.__doc__ = read.__doc__.format(name=self.name)

        def create(*, db: kwik.KwikSession = kwik.db, obj_in: CreateSchema) -> Any:
            """
            Create a {name}.
            """
            entity = self.crud.get(db, name=obj_in.name)
            if entity:
                raise HTTPException(
                    status_code=400, detail=f"The {self.name} with this name already exists in the system.",
                )
            obj_db = self.crud.create(db, obj_in=obj_in)
            return obj_db

        create.__doc__ = create.__doc__.format(name=self.name)

        def update(*, db: kwik.KwikSession = kwik.db, id: int, obj_in: UpdateSchema) -> Any:
            """
            Update a {name}.
            """
            db_obj = self.crud.get(db, id=id)
            if not db_obj:
                raise NotFound(id=id)
            return self.crud.update(db, db_obj=db_obj, obj_in=obj_in)

        update.__doc__ = update.__doc__.format(name=self.name)
        if custom_update is not None:
            update = custom_update(update)

        def delete(*, db: kwik.KwikSession = kwik.db, id: int) -> Any:
            """
            Delete a {name}.
            """
            obj_db = self.crud.get(db=db, id=id)
            if not obj_db:
                raise NotFound(id=id)
            return self.crud.remove(db=db, id=id)

        delete.__doc__ = delete.__doc__.format(name=self.name)

        deps = [kwik.current_user]
        if permissions is not None:
            deps.append(kwik.has_permission(*permissions))

        self.router.get("/", response_model=list[BaseSchema], dependencies=deps)(read_multi)
        self.router.get("/{id}", response_model=BaseSchema, dependencies=deps)(read)
        self.router.post("/", response_model=BaseSchema, dependencies=deps)(create)
        self.router.put("/{id}", response_model=BaseSchema, dependencies=deps)(update)
        self.router.delete("/{id}", dependencies=deps)(delete)

        api_router.include_router(self.router, prefix=f"/{self.name.replace('_', '/')}", tags=[f"{self.name}"])
        return self

    def add_endpoint(
        self, *, method: str, path: str, endpoint: Callable, response_model=None, permissions=None,
    ):
        register = {
            "get": self.router.get,
            "post": self.router.post,
            "put": self.router.put,
            "delete": self.router.delete,
        }

        response_model = response_model or self.BaseSchema
        deps = [kwik.current_user]
        if permissions is not None:
            deps.append(kwik.has_permission(*permissions))
        register[method](path, response_model=response_model, dependencies=deps)(endpoint)
