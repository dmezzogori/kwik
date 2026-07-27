"""Tests for the assert_max_queries testing helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text

from kwik.testing import assert_max_queries

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TestAssertMaxQueries:
    """Test cases for the assert_max_queries context manager."""

    def test_passes_when_query_count_is_within_limit(self, session: Session) -> None:
        """No error is raised when the executed query count is at or below the limit."""
        with assert_max_queries(session, 2):
            session.execute(text("SELECT 1"))
            session.execute(text("SELECT 2"))

    def test_fails_when_query_count_exceeds_limit(self, session: Session) -> None:
        """An AssertionError is raised when more queries than allowed are executed."""

        def _run_two_queries() -> None:
            with assert_max_queries(session, 1):
                session.execute(text("SELECT 1"))
                session.execute(text("SELECT 2"))

        with pytest.raises(AssertionError, match="2 queries"):
            _run_two_queries()

    def test_failure_message_includes_captured_statements(self, session: Session) -> None:
        """The AssertionError message lists the SQL statements that were executed."""

        def _run_one_query() -> None:
            with assert_max_queries(session, 0):
                session.execute(text("SELECT 42"))

        with pytest.raises(AssertionError, match="SELECT 42"):
            _run_one_query()

    def test_exposes_captured_statements(self, session: Session) -> None:
        """The context manager yields the list of captured SQL statements."""
        with assert_max_queries(session, 5) as statements:
            session.execute(text("SELECT 1"))

        assert len(statements) == 1
        assert "SELECT 1" in statements[0]

    def test_stops_capturing_after_exit(self, session: Session) -> None:
        """Statements executed after the context exits are not captured."""
        with assert_max_queries(session, 5) as statements:
            session.execute(text("SELECT 1"))

        session.execute(text("SELECT 2"))
        assert len(statements) == 1
