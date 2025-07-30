"""Test setup utilities and database management."""

from __future__ import annotations

from collections.abc import Callable

from kwik.database import DBContextManager
from kwik.database.base import Base


def init_test_db(init_db: Callable, *args, **kwargs) -> None:
    """Initialize test database with tables and seed data."""
    # Initialize the database
    with DBContextManager() as db:
        Base.metadata.create_all(bind=db.get_bind())
        init_db(*args, **kwargs)


def drop_test_db() -> None:
    """Drop all test database tables."""
    # Drop the database
    with DBContextManager() as db:
        Base.metadata.drop_all(bind=db.get_bind())
