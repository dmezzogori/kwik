"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.database import override_current_user
from kwik.database.context_vars import db_conn_ctx_var
from kwik.database.session_local import get_session_local
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session
if TYPE_CHECKING:
    from collections.abc import Generator

    from kwik.models import User


@pytest.fixture(autouse=True)
def db_session(setup_test_database: None) -> Generator[Session, None, None]:  # noqa: ARG001
    """Create a test database session with transaction rollback."""
    session_factory = get_session_local()
    session = session_factory()
    try:
        db_conn_ctx_var.set(session)
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def admin_user() -> User:
    """Create an admin user for CRUD operations."""
    return create_test_user(name="admin", surname="admin", email="admin@example.com", password="kwikisthebest")


@pytest.fixture(autouse=True)
def current_user(admin_user: User) -> Generator[None, None, None]:
    """Set up user context for CRUD operations."""
    with override_current_user(admin_user):
        yield
