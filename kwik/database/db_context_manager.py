from __future__ import annotations

from contextvars import Token
from typing import TYPE_CHECKING

from kwik.core.config import Settings
from kwik import models
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, Query

from .db_context_var import db_conn_ctx_var, current_user_ctx_var

if TYPE_CHECKING:
    from .session import KwikSession, KwikQuery

from contextlib import contextmanager


@contextmanager
def db_context_switcher():
    from kwik import settings

    prev_db_conn_ctx_var = db_conn_ctx_var.get()
    with DBContextManager(
        db_uri=settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI, settings=settings.alternate_db
    ) as db:
        yield db

    db_conn_ctx_var.set(prev_db_conn_ctx_var)


class DBSession:
    def __get__(self, obj, objtype=None) -> KwikSession:
        db = db_conn_ctx_var.get()
        if db is not None:
            return db
        raise Exception("No database connection available")


class CurrentUser:
    def __get__(self, obj, objtype=None) -> models.User | None:
        user = current_user_ctx_var.get()
        return user


class DBContextManager:
    """
    DB Session Context Manager.
    Correctly initialize the session by overriding the Session and Query class.
    Implemented as a python context manager, automatically rollback a transaction
    if any exception is raised by the application.
    """

    def __init__(
        self, *, settings: Settings | None = None, db_uri: str | None = None, connect_args: dict | None = None
    ) -> None:
        self.engine = create_engine(
            url=db_uri or settings.SQLALCHEMY_DATABASE_URI,
            pool_pre_ping=True,
            connect_args=connect_args if connect_args else {},
        )
        self.db: KwikSession | Session | None = None
        self.settings: Settings = settings
        self.token: Token | None = None

    def __enter__(self) -> KwikSession | Session:
        class_ = Session
        query_cls = Query
        if self.settings.ENABLE_SOFT_DELETE:
            from .session import KwikSession, KwikQuery

            class_ = KwikSession
            query_cls = KwikQuery

        self.db = sessionmaker(
            class_=class_,
            query_cls=query_cls,
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )()

        self.token = db_conn_ctx_var.set(self.db)
        return self.db

    def __exit__(self, exception_type, exception_value, exception_traceback) -> None:
        if exception_type is not None:
            self.db.rollback()
        else:
            self.db.commit()

        self.db.close()
        db_conn_ctx_var.reset(self.token)
