"""CRUD-specific pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.database.override_current_user import override_current_user
from tests.utils import create_test_user

if TYPE_CHECKING:
    from collections.abc import Generator

    from kwik.models import User


@pytest.fixture
def test_user() -> User:
    """Create a test user for CRUD operations."""
    return create_test_user(
        name="cruduser",
        surname="crudsurname",
        email="crud@example.com",
        password="crudpassword123",
    )


@pytest.fixture
def user_context(test_user: User) -> Generator[None, None, None]:
    """Set up user context for CRUD operations."""
    with override_current_user(test_user):
        yield
