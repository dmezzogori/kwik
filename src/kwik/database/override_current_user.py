"""Database current user context manager override for Kwik framework."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from kwik.database.context_vars import current_user_ctx_var

if TYPE_CHECKING:
    from collections.abc import Generator

    from kwik.models import User


@contextmanager
def override_current_user(user: User) -> Generator[None, Any, None]:
    """Context manager for setting and automatically cleaning up the current user context.

    This context manager sets the current user for CRUD operations and ensures
    proper cleanup even if exceptions occur. The try/finally block guarantees
    that the context variable token is always reset, preventing context leaks
    and ensuring the user context doesn't persist beyond its intended scope.

    Args:
        user: The User instance to set as the current user context.

    Yields:
        None: The context manager doesn't yield any value.

    Example:
        >>> from kwik.models import User
        >>> from kwik.crud import users
        >>> from kwik.database import override_current_user
        >>>
        >>> user = User(id=1, email="john_doe@example.com")
        >>> with override_current_user(user):
        ...     # Within this block, CRUD operations will have access to the current user
        ...     # via the current_user CRUD instance attribute.
        ...     users.current_user.email == user.email # True
        ...
        >>> # User context is automatically cleaned up here, even if an exception occurred

    """
    token = current_user_ctx_var.set(user)
    try:
        yield
    finally:
        current_user_ctx_var.reset(token)
