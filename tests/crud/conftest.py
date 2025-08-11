"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import sessionmaker

from kwik.crud import Context, NoUserCtx, UserCtx
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture
def no_user_context(engine: Engine) -> Generator[NoUserCtx, None, None]:
    """Create a test database session with transaction rollback."""
    session_maker = sessionmaker(bind=engine, autoflush=False)
    session = session_maker()
    try:
        yield Context(session=session, user=None)
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def admin_context(engine: Engine) -> Generator[UserCtx, None, None]:
    """Create a test database session with transaction rollback."""
    session_maker = sessionmaker(bind=engine, autoflush=False)
    session = session_maker()
    try:
        admin = create_test_user(
            name="admin",
            surname="surname",
            email="admin@example.com",
            password="password",
            is_active=True,
            context=Context(session=session, user=None),
        )
        yield Context(session=session, user=admin)
    finally:
        session.rollback()
        session.close()
