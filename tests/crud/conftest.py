"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.crud import Context, NoUserCtx, UserCtx

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models import User


@pytest.fixture
def no_user_context(db_session: Session) -> NoUserCtx:
    """Create a Context with no user for CRUD operations."""
    return Context(session=db_session, user=None)


@pytest.fixture
def admin_context(admin_user: User, db_session: Session) -> UserCtx:
    """Create a Context with shared admin user for CRUD operations."""
    return Context(session=db_session, user=admin_user)
