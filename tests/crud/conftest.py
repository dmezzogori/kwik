"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.crud import Context, NoUserCtx, UserCtx
from kwik.database import create_session, session_scope

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from kwik.models import User


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    """Create a database session with transaction rollback for test isolation."""
    session = create_session(engine=engine)
    with session_scope(session=session, commit=False) as session:
        yield session


@pytest.fixture
def no_user_context(session: Session) -> NoUserCtx:
    """Create a Context with no user for CRUD operations."""
    return Context(session=session, user=None)


@pytest.fixture
def admin_context(session: Session, admin_user: User) -> UserCtx:
    """Create a Context with shared admin user for CRUD operations."""
    return Context(session=session, user=admin_user)
