from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

from kwik.database.db_context_manager import DBContextManager
from kwik.database.session_local import AlternateSessionLocal
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

    if AlternateSessionLocal is None:
        raise ValueError("AlternateSessionLocal is not set. Check env variable ALTERNATE_SQLALCHEMY_DATABASE_URI")

    alternate_db_token = db_conn_ctx_var.set(AlternateSessionLocal())

    # Create a new database session.
    with DBContextManager() as db:
        yield db

    # Restore the previous database session in the context variable.
    db_conn_ctx_var.reset(alternate_db_token)
