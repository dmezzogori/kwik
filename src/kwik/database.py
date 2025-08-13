"""
Database engine creation and configuration module.

This module provides utilities for creating and configuring SQLAlchemy database engines
with optimized connection pool settings for the Kwik application.

Functions:
    create_engine: Creates a SQLAlchemy engine with connection pooling and validation.
    create_session_factory: Creates a SQLAlchemy session factory for database sessions.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session, sessionmaker

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
        the SQLALCHEMY_DATABASE_URI.

    Returns
    -------
    Engine
        Configured SQLAlchemy engine with connection pooling, pre-ping
        validation, and automatic connection recycling.

    """
    return _create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        # Connection pool settings
        pool_size=10,  # Core connections (adjust based on expected load)
        max_overflow=20,  # Additional connections during peak usage
        pool_pre_ping=True,  # Validates connections before use
        pool_recycle=3600,  # Recycle connections every hour (PostgreSQL default timeout is often 8 hours)
    )


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


__all__ = ["create_engine", "create_session", "create_session_factory", "session_scope"]
