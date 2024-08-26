from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

from kwik.database.context_vars import current_user_ctx_var

if TYPE_CHECKING:
    import kwik.models


@contextmanager
def CurrentUserContextManager(user: kwik.models.User) -> Generator[None, None, None]:
    """
    Context manager for the current user.

    Automatically manages the current user for the CRUD operations.
    """

    token = current_user_ctx_var.set(user)
    try:
        yield
    finally:
        current_user_ctx_var.reset(token)
