"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.database import override_current_user
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from kwik.models import User


@pytest.fixture(autouse=True)
def admin_user() -> User:
    """Create an admin user for CRUD operations."""
    return create_test_user(name="admin", surname="admin", email="admin@example.com", password="kwikisthebest")


@pytest.fixture(autouse=True)
def current_user(admin_user: User) -> Generator[None, None, None]:
    """Set up user context for CRUD operations."""
    with override_current_user(admin_user):
        yield
