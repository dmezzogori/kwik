from __future__ import annotations

from typing import Type, Optional

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, Query

from kwik.core.config import Settings
from kwik.db import SoftDeleteMixin, Base


class KwikSession(Session):
    def delete(self, instances) -> None:
        for instance in instances:
            if _has_soft_delete(type(instance)):
                instance.deleted = True


class KwikQuery(Query):
    def __init__(self, entities: tuple[Type[Base], ...], session: Session = None) -> None:
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
        self._where_criteria = [c for c in self._where_criteria if c not in self._soft_delete_criteria]
        return self

    def join(self, target, *args, **kwargs):
        if _has_soft_delete(target):
            self._where_criteria += (target.deleted == False,)
        return super().join(target, *args, **kwargs)


class DBContextManager:
    def __init__(self, settings: Settings, db_uri: Optional[str] = None) -> None:
        engine = create_engine(db_uri or settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
        db = sessionmaker(class_=KwikSession, query_cls=KwikQuery, autocommit=False, autoflush=False, bind=engine,)()
        self.db = db

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, exception_type, exception_value, exception_traceback) -> None:
        if exception_type is not None:
            self.db.rollback()
        else:
            self.db.commit()

        self.db.close()


def _has_soft_delete(entity: Type[Base]) -> bool:
    return issubclass(entity, SoftDeleteMixin)


def get_db_from_request(request: Request) -> Session:
    return request.state.db
