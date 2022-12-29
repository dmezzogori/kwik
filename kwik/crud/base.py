from __future__ import annotations

import abc
from typing import Any, Type, TYPE_CHECKING, Generic, get_args, NoReturn

from kwik.database import db_context_manager
from kwik.models import User
from kwik.typings import ModelType, CreateSchemaType, UpdateSchemaType
from kwik.typings import ParsedSortingQuery, PaginatedCRUDResult

if TYPE_CHECKING:
    from kwik.database.session import KwikSession

T = Generic[ModelType, CreateSchemaType, UpdateSchemaType]


class CRUDBase(abc.ABC, Generic[ModelType]):
    db: KwikSession = db_context_manager.DBSession()
    user: User | None = db_context_manager.CurrentUser()
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
