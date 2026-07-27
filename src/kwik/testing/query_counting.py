"""Query-counting helpers for asserting database access patterns in tests."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import event

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


@contextmanager
def assert_max_queries(session: Session, max_queries: int) -> Generator[list[str], None, None]:
    """
    Assert that the code in the block executes at most ``max_queries`` SQL statements.

    Captures every statement sent to the session's bind while the block runs and
    raises ``AssertionError`` on exit when the count exceeds the limit, listing the
    captured statements to make N+1 regressions easy to diagnose.

    Args:
        session: The SQLAlchemy session whose bind should be instrumented.
        max_queries: Maximum number of SQL statements the block may execute.

    Yields:
        The live list of captured SQL statements (useful for further inspection).

    Raises:
        AssertionError: If more than ``max_queries`` statements were executed.

    Example:
        with assert_max_queries(session, 3):
            crud_resources.get_multi(context=context)

    """
    statements: list[str] = []
    bind = session.get_bind()

    def _capture(*args: Any) -> None:  # noqa: ANN401
        statements.append(args[2])

    event.listen(bind, "before_cursor_execute", _capture)
    try:
        yield statements
    finally:
        event.remove(bind, "before_cursor_execute", _capture)

    if len(statements) > max_queries:
        formatted = "\n".join(f"  {i}. {stmt}" for i, stmt in enumerate(statements, 1))
        msg = f"Expected at most {max_queries} queries, but {len(statements)} queries were executed:\n{formatted}"
        raise AssertionError(msg)


__all__ = ["assert_max_queries"]
