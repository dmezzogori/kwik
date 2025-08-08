"""Database db context switcher for Kwik framework."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from kwik.database.context_vars import db_conn_ctx_var
from kwik.database.db_context_manager import DBContextManager
from kwik.database.session_local import get_alternate_session_local

if TYPE_CHECKING:
    from collections.abc import Generator

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
    alternate_session_local = get_alternate_session_local()
    if alternate_session_local is None:
        msg = "AlternateSessionLocal is not set. Check env variable ALTERNATE_SQLALCHEMY_DATABASE_URI"
        raise ValueError(msg)

    alternate_db_token = db_conn_ctx_var.set(alternate_session_local())

    # Create a new database session.
    with DBContextManager() as db:
        yield db

    # Restore the previous database session in the context variable.
    db_conn_ctx_var.reset(alternate_db_token)
