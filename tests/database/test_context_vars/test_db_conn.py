"""Tests for database connection context variable."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

from kwik.database.context_vars.db_conn import db_conn_ctx_var

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@pytest.mark.usefixtures("clean_context_vars")
class TestDbConnContextVar:
    """Test suite for db_conn_ctx_var context variable."""

    def test_default_value_is_none(self) -> None:
        """Test that the default value of db_conn_ctx_var is None."""
        assert db_conn_ctx_var.get() is None

    def test_set_and_get_session(self, mock_session: Session) -> None:
        """Test setting and getting a Session object."""
        token = db_conn_ctx_var.set(mock_session)

        try:
            retrieved_session = db_conn_ctx_var.get()
            assert retrieved_session is mock_session
        finally:
            db_conn_ctx_var.reset(token)

    def test_token_management(self, mock_session: Session) -> None:
        """Test proper token-based context management."""
        # Initial state
        assert db_conn_ctx_var.get() is None

        # Set first value
        token1 = db_conn_ctx_var.set(mock_session)
        assert db_conn_ctx_var.get() is mock_session

        # Set second value (nested)
        different_mock = type(mock_session)()
        token2 = db_conn_ctx_var.set(different_mock)
        assert db_conn_ctx_var.get() is different_mock

        # Reset to first value
        db_conn_ctx_var.reset(token2)
        assert db_conn_ctx_var.get() is mock_session

        # Reset to original state
        db_conn_ctx_var.reset(token1)
        assert db_conn_ctx_var.get() is None

    def test_context_isolation_between_threads(self, mock_session: Session) -> None:
        """Test that context variables are isolated between threads."""
        results = {}

        def thread1_work() -> None:
            # Thread 1 sets its own session
            thread1_session = type(mock_session)()
            token = db_conn_ctx_var.set(thread1_session)
            try:
                results["thread1"] = db_conn_ctx_var.get()
            finally:
                db_conn_ctx_var.reset(token)

        def thread2_work() -> None:
            # Thread 2 should not see thread 1's session
            results["thread2"] = db_conn_ctx_var.get()

            # Thread 2 sets its own session
            thread2_session = type(mock_session)()
            token = db_conn_ctx_var.set(thread2_session)
            try:
                results["thread2_with_session"] = db_conn_ctx_var.get()
            finally:
                db_conn_ctx_var.reset(token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(thread1_work)
            future2 = executor.submit(thread2_work)

            future1.result()
            future2.result()

        # Each thread should have its own isolated context
        assert results["thread2"] is None  # Thread 2 didn't see thread 1's session
        assert results["thread1"] is not None
        assert results["thread2_with_session"] is not None
        assert results["thread1"] is not results["thread2_with_session"]

    @pytest.mark.asyncio
    async def test_async_context_isolation(self, mock_session: Session) -> None:
        """Test that context variables work correctly in async contexts."""
        results = {}

        async def task1() -> None:
            # Task 1 sets its own session
            task1_session = type(mock_session)()
            token = db_conn_ctx_var.set(task1_session)
            try:
                # Yield control to allow task2 to run
                await asyncio.sleep(0.01)
                results["task1"] = db_conn_ctx_var.get()
            finally:
                db_conn_ctx_var.reset(token)

        async def task2() -> None:
            # Task 2 should not see task 1's session
            results["task2_initial"] = db_conn_ctx_var.get()

            # Task 2 sets its own session
            task2_session = type(mock_session)()
            token = db_conn_ctx_var.set(task2_session)
            try:
                # Yield control
                await asyncio.sleep(0.01)
                results["task2"] = db_conn_ctx_var.get()
            finally:
                db_conn_ctx_var.reset(token)

        # Run tasks concurrently
        await asyncio.gather(task1(), task2())

        # Each task should have its own isolated context
        assert results["task2_initial"] is None  # Task 2 didn't see task 1's session
        assert results["task1"] is not None
        assert results["task2"] is not None
        assert results["task1"] is not results["task2"]

    def test_none_value_handling(self, mock_session: Session) -> None:
        """Test that None can be explicitly set and retrieved."""
        # Set a session first
        token1 = db_conn_ctx_var.set(mock_session)
        assert db_conn_ctx_var.get() is mock_session

        # Explicitly set None
        token2 = db_conn_ctx_var.set(None)
        assert db_conn_ctx_var.get() is None

        # Reset should restore previous value
        db_conn_ctx_var.reset(token2)
        assert db_conn_ctx_var.get() is mock_session

        # Final cleanup
        db_conn_ctx_var.reset(token1)
        assert db_conn_ctx_var.get() is None

    def test_nested_contexts_with_same_value(self, mock_session: Session) -> None:
        """Test nested contexts with the same value."""
        # Set same session twice (nested)
        token1 = db_conn_ctx_var.set(mock_session)
        token2 = db_conn_ctx_var.set(mock_session)  # Same session

        assert db_conn_ctx_var.get() is mock_session

        # Reset inner context
        db_conn_ctx_var.reset(token2)
        assert db_conn_ctx_var.get() is mock_session  # Should still be the same session

        # Reset outer context
        db_conn_ctx_var.reset(token1)
        assert db_conn_ctx_var.get() is None

    @pytest.mark.asyncio
    async def test_context_inheritance_in_tasks(self, mock_session: Session) -> None:
        """Test that child tasks inherit parent context but can override it."""
        results = {}

        # Parent sets context
        token = db_conn_ctx_var.set(mock_session)

        try:

            async def child_task() -> None:
                # Child should inherit parent's context
                results["inherited"] = db_conn_ctx_var.get()

                # Child can override with its own context
                child_session = type(mock_session)()
                child_token = db_conn_ctx_var.set(child_session)
                try:
                    results["child_override"] = db_conn_ctx_var.get()
                finally:
                    db_conn_ctx_var.reset(child_token)

                # After reset, should see parent's context again
                results["after_reset"] = db_conn_ctx_var.get()

            await child_task()

            # Parent context should still be active
            results["parent_final"] = db_conn_ctx_var.get()

        finally:
            db_conn_ctx_var.reset(token)

        # Verify context inheritance and isolation
        assert results["inherited"] is mock_session
        assert results["child_override"] is not mock_session
        assert results["after_reset"] is mock_session
        assert results["parent_final"] is mock_session

    def test_invalid_token_reset_raises_runtime_error(self, mock_session: Session) -> None:
        """Test that resetting with invalid token raises RuntimeError."""
        token = db_conn_ctx_var.set(mock_session)

        # Reset once (valid)
        db_conn_ctx_var.reset(token)

        # Reset again with same token (invalid) - Python raises RuntimeError, not LookupError
        with pytest.raises(RuntimeError, match="has already been used once"):
            db_conn_ctx_var.reset(token)

    def test_context_var_name_and_default(self) -> None:
        """Test context variable has correct name and default."""
        assert db_conn_ctx_var.name == "db_conn_ctx_var"
        assert db_conn_ctx_var.get("test_default") is None
        assert db_conn_ctx_var.get() is None
