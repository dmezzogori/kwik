import abc
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from kwik.database.base import Base
from kwik.database.session import KwikSession
from kwik.models import User
from kwik.typings import ParsedSortingQuery, PaginatedCRUDResult

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(abc.ABC):
    model: Type[ModelType]

    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model


class CRUDReadBase(CRUDBase):
    @abc.abstractmethod
    def get(self, *, db: KwikSession, id: int) -> ModelType | None:
        pass

    @abc.abstractmethod
    def get_multi(
        self,
        *,
        db: KwikSession,
        skip: int = 0,
        limit: int = 100,
        sort: ParsedSortingQuery | None = None,
        **filters
    ) -> PaginatedCRUDResult:
        pass


class CRUDCreateBase(CRUDBase):
    @abc.abstractmethod
    def create(
        self, *, db: KwikSession, obj_in: CreateSchemaType, user: User | None = None
    ) -> ModelType:
        pass

    @abc.abstractmethod
    def create_if_not_exist(
        self,
        *,
        db: KwikSession,
        obj_in: CreateSchemaType,
        user: User | None = None,
        raise_on_error: bool = False,
        **kwargs
    ) -> ModelType:
        pass


class CRUDUpdateBase(CRUDBase):
    @abc.abstractmethod
    def update(
        self,
        *,
        db: KwikSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        user: User | None = None
    ) -> ModelType:
        pass


class CRUDDeleteBase(CRUDBase):
    @abc.abstractmethod
    def delete(
        self, *, db: KwikSession, id: int, user: User | None = None
    ) -> ModelType:
        pass


class AutoCRUDBase(
    CRUDCreateBase, CRUDReadBase, CRUDUpdateBase, CRUDDeleteBase, abc.ABC
):
    pass
