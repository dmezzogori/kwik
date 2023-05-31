from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Generic, NoReturn, Type, get_args

import kwik
from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var
from kwik.models import User
from kwik.typings import (
    CreateSchemaType,
    ModelType,
    PaginatedCRUDResult,
    ParsedSortingQuery,
    UpdateSchemaType,
)

if TYPE_CHECKING:
    from kwik.database.session import KwikSession
    from sqlalchemy.orm import Session

T = Generic[ModelType, CreateSchemaType, UpdateSchemaType]


class DBSession:
    def __get__(self, obj, objtype=None) -> Session:
        if (db := db_conn_ctx_var.get()) is not None:
            return db
        raise Exception("No database connection available")


class CurrentUser:
    def __get__(self, obj, objtype=None) -> kwik.models.User | None:
        user = current_user_ctx_var.get()
        return user


class CRUDBase(abc.ABC, Generic[ModelType]):
    db: KwikSession = DBSession()
    user: User | None = CurrentUser()
    model: Type[ModelType]

    _instances: dict[str, T] = {}

    def __init__(self, model: Type[ModelType] | None = None):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        """
        _model = model if model is not None else get_args(self.__orig_bases__[0])[0]
        self.model = _model
        CRUDBase._instances[_model] = self

    @classmethod
    def get_instance(cls: T, model: Type[ModelType]) -> T:
        return CRUDBase._instances[model]


class CRUDReadBase(CRUDBase[ModelType]):
    @abc.abstractmethod
    def get(self, *, id: int) -> ModelType | None:
        pass

    @abc.abstractmethod
    def get_all(self) -> list[ModelType]:
        pass

    @abc.abstractmethod
    def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters,
    ) -> PaginatedCRUDResult[ModelType]:
        pass

    @abc.abstractmethod
    def get_if_exist(self, *, id: int) -> ModelType | NoReturn:
        pass


class CRUDCreateBase(CRUDBase, Generic[ModelType, CreateSchemaType]):
    @abc.abstractmethod
    def create(
        self,
        *,
        obj_in: CreateSchemaType,
    ) -> ModelType:
        pass

    @abc.abstractmethod
    def create_if_not_exist(
        self,
        *,
        obj_in: CreateSchemaType,
        filters: dict[str, str],
        raise_on_error: bool = False,
    ) -> ModelType:
        pass


class CRUDUpdateBase(CRUDBase, Generic[ModelType, UpdateSchemaType]):
    @abc.abstractmethod
    def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        pass


class CRUDDeleteBase(CRUDBase[ModelType]):
    @abc.abstractmethod
    def delete(self, *, id: int) -> ModelType:
        pass
