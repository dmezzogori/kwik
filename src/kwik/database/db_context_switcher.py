from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

from kwik.database import DBContextManager
from kwik.database.context_vars import db_conn_ctx_var

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@contextmanager
def DBContextSwitcher() -> Generator[Session, None, None]:  # noqa: N802
    """
    Context manager to switch to an alternate database.

    Example:
    with db_context_switcher():
        # Do something with the alternate database.
        pass
    """

    # Get the current database session from the context variable.
    prev_db_conn_ctx_var = db_conn_ctx_var.get()

    # Create a new database session.
    with DBContextManager() as db:
        yield db

    # Restore the previous database session in the context variable.
    db_conn_ctx_var.set(prev_db_conn_ctx_var)
