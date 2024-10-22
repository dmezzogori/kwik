from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

from kwik.database.context_vars import db_conn_ctx_var
from kwik.database.session_local import SessionLocal


if TYPE_CHECKING:
    from contextvars import Token

    from sqlalchemy.orm import Session


class DBContextManager:
    """
    DB Session Context Manager.

    Implemented as a context manager,
    automatically rollback a transaction if any exception is raised by the application.
    """

    def __init__(self) -> None:
        """
        Initialize the DBContextManager.
        """

        self.db: Session | None = None
        self.token: Token[Session | None] | None = None

    def __enter__(self) -> Session:
        """
        Enter the context manager, which returns a database session.

        Retrieves a database session from the context variable.
        If no session is found, a new session is created and stored in the context variable.

        Returns a database session.
        """

        db = db_conn_ctx_var.get()
        if db is None:
            # No session found in the context variable.

            # Create a new session.
            self.db = SessionLocal()
            # Store the session in the context variable.
            self.token = db_conn_ctx_var.set(self.db)
        else:
            # Session found in the context variable.
            self.db = db

        return self.db

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        exception_traceback: TracebackType | None,
    ) -> None:
        """
        Exit the context manager, handling any exceptions raised by the application.

        If an exception is raised by the application, rollback the transaction.
        Otherwise, commit the transaction.

        Then, closes the database session and reset the context variable to its previous value.
        """

        if exception_type is not None:
            # An exception was raised by the application.

            # Rollback the transaction.
            self.db.rollback()
        else:
            # No exception was raised by the application.

            # Commit the transaction.
            self.db.commit()

        # Close the database session.
        self.db.close()

        # Reset the context variable to its previous value.
        db_conn_ctx_var.set(None)
