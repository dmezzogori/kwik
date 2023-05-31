from __future__ import annotations

from contextlib import contextmanager
from contextvars import Token
from typing import TYPE_CHECKING

import kwik
from kwik import models
from kwik.core.config import Settings
from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from .session import KwikSession


@contextmanager
def db_context_switcher():
    from kwik import settings

    prev_db_conn_ctx_var = db_conn_ctx_var.get()
    with DBContextManager(
        db_uri=settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI,
        settings=settings.alternate_db,
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


engine = create_engine(
    url=kwik.settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=kwik.settings.POSTGRES_MAX_CONNECTIONS // kwik.settings.BACKEND_WORKERS,
    max_overflow=0,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class DBContextManager:
    """
    DB Session Context Manager.

    Implemented as a context manager,
    automatically rollback a transaction if any exception is raised by the application.
    """

    def __init__(self, *, settings: Settings) -> None:
        """
        Initialize the DBContextManager.

        Requires a Settings object instance to be passed in.
        """
        self.settings: Settings = settings
        self.db: KwikSession | Session | None = None
        self.token: Token | None = None

    def __enter__(self) -> KwikSession | Session:
        """
        Enter the context manager.

        Returns a database session.
        """

        token = db_conn_ctx_var.get()
        if token is not None:
            self.db = token
            self.token = token
            return self.db

        self.db = SessionLocal()

        self.token = db_conn_ctx_var.set(self.db)
        return self.db

    def __exit__(self, exception_type, exception_value, exception_traceback) -> None:
        if exception_type is not None:
            self.db.rollback()
        else:
            self.db.commit()

        self.db.close()
        db_conn_ctx_var.reset(self.token)
