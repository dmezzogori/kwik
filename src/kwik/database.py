"""
Database engine creation and configuration module.

This module provides utilities for creating and configuring SQLAlchemy database engines
with optimized connection pool settings for the Kwik application.

Functions:
    create_engine: Creates a SQLAlchemy engine with connection pooling and validation.
    create_session_factory: Creates a SQLAlchemy session factory for database sessions.
    warn_if_pool_exceeds_connections: Warns when the worker pools can exceed the connection limit.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session, sessionmaker

from kwik.logging import logger

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine

    from kwik.settings import BaseKwikSettings


def create_engine(settings: BaseKwikSettings) -> Engine:
    """
    Create a SQLAlchemy engine with optimized connection pool settings.

    Parameters
    ----------
    settings : BaseKwikSettings
        Application settings containing database configuration including
        the SQLALCHEMY_DATABASE_URI and the pool settings
        (POSTGRES_POOL_SIZE, POSTGRES_MAX_OVERFLOW, POSTGRES_POOL_TIMEOUT).

    Returns
    -------
    Engine
        Configured SQLAlchemy engine with connection pooling, pre-ping
        validation, and automatic connection recycling. A checkout that finds
        the pool exhausted fails after POSTGRES_POOL_TIMEOUT seconds.

    """
    return _create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        # Connection pool settings (per worker process)
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        pool_timeout=settings.POSTGRES_POOL_TIMEOUT,
        pool_pre_ping=True,  # Validates connections before use
        pool_recycle=3600,  # Recycle connections every hour (PostgreSQL default timeout is often 8 hours)
    )


def warn_if_pool_exceeds_connections(settings: BaseKwikSettings) -> bool:
    """
    Log a warning when the worker pools together can exceed the database's connection limit.

    Each worker process has its own pool of ``POSTGRES_POOL_SIZE + POSTGRES_MAX_OVERFLOW``
    connections, so ``BACKEND_WORKERS`` pools can open that many times as many.

    Returns
    -------
    bool
        True when it warned.

    """
    per_worker = settings.POSTGRES_POOL_SIZE + settings.POSTGRES_MAX_OVERFLOW
    total = settings.BACKEND_WORKERS * per_worker
    if total <= settings.POSTGRES_MAX_CONNECTIONS:
        return False
    logger.warning(
        f"{settings.BACKEND_WORKERS} workers x {per_worker} pooled connections = {total} "
        f"exceeds POSTGRES_MAX_CONNECTIONS={settings.POSTGRES_MAX_CONNECTIONS}",
    )
    return True


def create_session_factory(engine: Engine) -> sessionmaker:
    """
    Create a SQLAlchemy session factory.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine to use for creating sessions.

    Returns
    -------
    sessionmaker
        A configured session factory for creating database sessions.

    """
    return sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,  # prevents lazy loading issues after commit
        autoflush=True,  # Default, but explicit is better - flushes before queries
        autocommit=False,  # Default - use explicit transactions
    )


def create_session(engine: Engine) -> Session:
    """
    Create a new SQLAlchemy session.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine to use for creating the session.

    Returns
    -------
    Session
        A new SQLAlchemy session instance.

    """
    session_maker = create_session_factory(engine=engine)
    return session_maker()


@contextmanager
def session_scope(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "create_engine",
    "create_session",
    "create_session_factory",
    "session_scope",
    "warn_if_pool_exceeds_connections",
]
