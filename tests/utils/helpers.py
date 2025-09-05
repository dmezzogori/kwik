"""Helper functions for testing database operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.testing import Scenario

if TYPE_CHECKING:
    from kwik.crud import NoUserCtx
    from kwik.models import User


def create_test_user(  # noqa: PLR0913
    *,
    name: str = "testuser",
    surname: str = "testsurname",
    email: str = "test@example.com",
    password: str = "testpassword123",
    is_active: bool = True,
    context: NoUserCtx,
) -> User:
    """Create a test user with the specified parameters."""
    scenario = Scenario().with_user(
        name=name,
        surname=surname,
        email=email,
        password=password,
        is_active=is_active,
    )
    result = scenario.build(session=context.session)
    return result.users[name]
