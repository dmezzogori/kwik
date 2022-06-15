from __future__ import annotations

from collections.abc import Iterable
from typing import Sequence

import kwik
import kwik.crud
import kwik.crud.base
import kwik.schemas
import kwik.typings
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, Query
from sqlalchemy.sql.elements import Label


class KwikSession(Session):
    """
    Kwik extension of the SQLAlchemy Session class.
    Needed to override the delete method (i.e. database.delete(some_instance))
    to implement the Soft Delete pattern.
    It is automatically registered by the DBContextManager.
    """

    def query(self, *entities, **kwargs) -> KwikQuery:
        return super().query(*entities, **kwargs)

    def delete(self, instances: kwik.typings.ModelType | Sequence[kwik.typings.ModelType]) -> None:
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
    It is automatically registered by the Kwik DBContextManager.
    """

    def __init__(self, entities: tuple[kwik.typings.ModelType, ...], session: Session = None) -> None:
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

    def filter(self, *criterion) -> KwikQuery:
        super().filter(*criterion)
        return self

    def order_by(self, *clauses) -> KwikQuery:
        super().order_by(*clauses)
        return self

    def limit(self, limit) -> KwikQuery:
        super().limit(limit)
        return self

    def offset(self, offset) -> KwikQuery:
        super().offset(offset)
        return self

    @property
    def soft_delete_enabled(self) -> bool:
        return len(self._soft_delete_criteria) > 0

    def ignore_soft_delete(self) -> KwikQuery:
        """
        Additional method to explicitly disable the application
        of soft delete filter in SELECT statements.
        i.e. database.query(some_model_with_soft_delete).ignore_soft_delete().all()
        return all records, ignoring soft delete flags.
        """
        self._where_criteria = [c for c in self._where_criteria if c not in self._soft_delete_criteria]
        return self

    def get(self, ident: int):
        if self.soft_delete_enabled:
            orig_where_criteria = list(self._where_criteria)
            self._where_criteria = []
            result = super().get(ident)
            self._where_criteria = orig_where_criteria
            return result if not result.deleted else None
        else:
            return super().get(ident)

    def join(self, target, *args, **kwargs) -> KwikQuery:
        """
        Automatically inject soft delete filters for target models involved in a join.
        i.e. database.query(some_model).join(other_model_with_soft_delete) automatically add
        a filter condition on the joined table.
        """
        if _has_soft_delete(target):
            self._where_criteria += (target.deleted == False,)
        return super().join(target, *args, **kwargs)

    def outerjoin(self, target, *props, **kwargs) -> KwikQuery:
        """
        Automatically inject soft delete filters for target models involved in a join.
        i.e. database.query(some_model).outerjoin(other_model_with_soft_delete) automatically add
        a filter condition on the joined table.
        """
        if _has_soft_delete(target):
            self._where_criteria += (target.deleted == False,)
        return super().outerjoin(target, *props, **kwargs)


def _has_soft_delete(model: kwik.typings.ModelType) -> bool:
    """
    Checks if an entity (model class) is marked to implement
    the soft delete pattern (i.e. is a subclass of SoftDeleteMixin)
    """
    t = model
    if hasattr(t, "class_"):
        t = model.class_
    elif isinstance(t, Label):
        # noinspection PyProtectedMember
        if hasattr(t._element, "table"):
            # noinspection PyProtectedMember
            columns = t._element.table.columns
        else:
            # noinspection PyProtectedMember
            columns = t._element.columns
        for col in columns:
            *_, col_name = col.name.split(".")
            if col_name == "deleted":
                return True
        return False

    return issubclass(t, kwik.database.mixins.SoftDeleteMixin)


def _to_be_logged(model: kwik.typings.ModelType) -> bool:
    return issubclass(model, kwik.database.mixins.LogMixin)


def _to_be_audited(model: kwik.typings.ModelType) -> bool:
    return issubclass(model, kwik.database.mixins.RecordInfoMixin)


def get_db_from_request(request: Request) -> KwikSession:
    """
    Returns the session instance attached to a Kwik request.
    """
    return request.state.db
