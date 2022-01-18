from __future__ import annotations

from collections.abc import Iterable
from typing import Sequence

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, Query

import kwik.typings
from kwik.core.config import Settings


class KwikSession(Session):
    """
    Kwik extension of the SQLAlchemy Session class.
    Needed to override the delete method (i.e. database.delete(some_instance))
    to implement the Soft Delete pattern.
    It is automatically registered by the DBContextManager.
    """

    def query(self, *entities, **kwargs) -> KwikQuery:
        ...

    def delete(
        self, instances: kwik.typings.ModelType | Sequence[kwik.typings.ModelType]
    ) -> None:
        if not isinstance(instances, Iterable):
            instances = (instances,)
        for instance in instances:
            if _has_soft_delete(type(instance)):
                instance.deleted = True
            else:
                super().delete(instance)

                if kwik.settings.DB_LOGGER and _to_be_logged(type(instance)):
                    log_in = kwik.schemas.LogCreateSchema(
                        request_id=kwik.middlewares.get_request_id(),
                        entity=instance.__tablename__,
                        before=jsonable_encoder(instance),
                        after=None,
                    )
                    kwik.crud.logs.create(db=self, obj_in=log_in)


class KwikQuery(Query):
    """
    Kwik extension of the SQLAlchemy Query class.
    Needed to override the instantiation of the class (i.e. database.query(some_model)),
    and the join method(i.e. database.query(some_model).join(other_model)),
    to implement the Soft Delete pattern.
    It is automatically registered by the DBContextManager.
    """

    def __init__(
        self, entities: tuple[kwik.typings.ModelType, ...], session: Session = None
    ) -> None:
        """
        Ovverides the superclass init to inject automatically soft delete
        filters, for any entity which requires that.
        """
        super().__init__(entities, session=session)

        self._soft_delete_criteria = []

        if not isinstance(entities, tuple):
            entities = (entities,)

        for entity in entities:
            if _has_soft_delete(entity):
                criterion = entity.deleted == False
                self._soft_delete_criteria += (criterion,)
                self._where_criteria += (criterion,)

    def ignore_soft_delete(self) -> KwikQuery:
        """
        Additional method to explicitly disable the application
        of soft delete filter in SELECT statements.
        i.e. database.query(some_model_with_soft_delete).ignore_soft_delete().all()
        return all records, ignoring soft delete flags.
        """
        self._where_criteria = [
            c for c in self._where_criteria if c not in self._soft_delete_criteria
        ]
        return self

    def join(self, target, *args, **kwargs):
        """
        Automatically inject soft delete filters for target models involved in a join.
        i.e. database.query(some_model).join(other_model_with_soft_delete) automatically add
        a filter condition on the joined table.
        """
        if _has_soft_delete(target):
            self._where_criteria += (target.deleted == False,)
        return super().join(target, *args, **kwargs)


class DBContextManager:
    """
    DB Session Context Manager.
    Correctly initialize the session by overriding the Session and Query class.
    Implemented as a python context manager, automatically rollback a transaction
    if any exception is raised by the application.
    """

    def __init__(
        self, *, settings: Settings | None = None, db_uri: str | None = None
    ) -> None:
        engine = create_engine(
            db_uri or settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True
        )
        db = sessionmaker(
            class_=KwikSession,
            query_cls=KwikQuery,
            autocommit=False,
            autoflush=False,
            bind=engine,
        )()
        self.db: KwikSession = db

    def __enter__(self) -> KwikSession:
        return self.db

    def __exit__(self, exception_type, exception_value, exception_traceback) -> None:
        if exception_type is not None:
            self.db.rollback()
        else:
            self.db.commit()

        self.db.close()


def _has_soft_delete(model: kwik.typings.ModelType) -> bool:
    """
    Checks if an entity (model class) is marked to implement
    the soft delete pattern (i.e. is a subclass of SoftDeleteMixin)
    """
    return issubclass(model, kwik.db.mixins.SoftDeleteMixin)


def _to_be_logged(model: kwik.typings.ModelType) -> bool:
    return issubclass(model, kwik.db.mixins.LogMixin)


def get_db_from_request(request: Request) -> KwikSession:
    """
    Returns the session instance attached to a Kwik request.
    """
    return request.state.db
