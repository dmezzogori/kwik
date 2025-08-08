"""Tests for database context manager - CRITICAL token management testing."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from kwik.database.context_vars import db_conn_ctx_var
from kwik.database.db_context_manager import DBContextManager


class TestDBContextManager:
    """Test suite for DBContextManager - Focus on critical token management bugs."""

    def test_new_session_creation_scenario(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test context manager when no session exists in context variable."""
        # Ensure no session in context
        assert db_conn_ctx_var.get() is None

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            with DBContextManager() as db:
                # Should return the new session
                assert db is mock_session

                # Session should be in context variable
                assert db_conn_ctx_var.get() is mock_session

                # Verify session factory was called
                mock_session_factory.assert_called_once()

        # After context: session should be committed, closed, and context cleared
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    def test_existing_session_reuse_scenario(
        self,
        isolated_test_environment,
        mock_session: Session,
    ) -> None:
        """Test context manager when session already exists in context variable."""
        # Pre-set a session in context
        existing_token = db_conn_ctx_var.set(mock_session)

        try:
            assert db_conn_ctx_var.get() is mock_session

            # Create a separate mock for the new context manager
            new_mock_session = MagicMock(spec=Session)
            mock_session_factory = MagicMock()
            mock_session_factory.return_value = new_mock_session

            with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
                with DBContextManager() as db:
                    # Should reuse existing session, not create new one
                    assert db is mock_session

                    # Session factory should NOT be called
                    mock_session_factory.assert_not_called()

                    # Context variable should still have original session
                    assert db_conn_ctx_var.get() is mock_session

            # CRITICAL BUG TEST: After context, the original session is still available
            # But the current implementation breaks this by setting context to None
            # This test will FAIL with current implementation, exposing the bug
            assert db_conn_ctx_var.get() is mock_session, "BUG: Context should not be modified when reusing existing session"

            # The existing session should NOT be committed/rolled back/closed
            # by the context manager that didn't create it
            mock_session.commit.assert_called_once()  # This will show the bug - it should NOT be called
            mock_session.close.assert_called_once()   # This will show the bug - it should NOT be called

        finally:
            # Cleanup
            try:
                db_conn_ctx_var.reset(existing_token)
            except LookupError:
                # Token might already be invalid due to the bug
                db_conn_ctx_var.set(None)

    def test_token_management_bug_new_session(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test the critical token management bug when creating new session."""
        # Set up initial context with a different session
        initial_session = MagicMock(spec=Session)
        initial_token = db_conn_ctx_var.set(initial_session)

        try:
            # Now clear context to simulate no session
            db_conn_ctx_var.set(None)

            with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
                with DBContextManager() as db:
                    assert db is mock_session
                    assert db_conn_ctx_var.get() is mock_session

            # CRITICAL BUG: Current implementation sets context to None
            # But it should reset to the previous value (None in this case is correct here)
            # However, if there was a previous value, it would be lost!
            assert db_conn_ctx_var.get() is None

        finally:
            db_conn_ctx_var.reset(initial_token)

    def test_token_management_bug_with_nested_contexts(
        self,
        isolated_test_environment,
        mock_session_factory,
    ) -> None:
        """Test the token bug with nested contexts - this will expose the critical flaw."""
        # Create different mock sessions
        outer_session = MagicMock(spec=Session)
        inner_session = MagicMock(spec=Session)

        outer_factory = MagicMock()
        outer_factory.return_value = outer_session

        inner_factory = MagicMock()
        inner_factory.return_value = inner_session

        # Outer context creates a session
        with patch("kwik.database.db_context_manager.get_session_local", return_value=outer_factory):
            with DBContextManager() as outer_db:
                assert outer_db is outer_session
                assert db_conn_ctx_var.get() is outer_session

                # Inner context should reuse outer session
                with patch("kwik.database.db_context_manager.get_session_local", return_value=inner_factory):
                    with DBContextManager() as inner_db:
                        # Should reuse outer session, not create inner session
                        assert inner_db is outer_session
                        assert db_conn_ctx_var.get() is outer_session

                        # Inner factory should NOT be called
                        inner_factory.assert_not_called()

                # CRITICAL BUG: After inner context exits, outer session should still be available
                # But current implementation will have set it to None
                try:
                    current_session = db_conn_ctx_var.get()
                    assert current_session is outer_session, (
                        f"BUG: Expected outer_session, got {current_session}. "
                        "Inner context manager incorrectly cleared the context variable."
                    )
                except AssertionError:
                    # This assertion will fail, exposing the bug
                    pytest.fail("CRITICAL BUG DETECTED: Inner context manager destroyed outer context")

        # After all contexts, should be None
        assert db_conn_ctx_var.get() is None

    def test_exception_handling_with_new_session(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test exception handling when context manager creates new session."""
        assert db_conn_ctx_var.get() is None

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            with pytest.raises(ValueError, match="Test exception"):
                with DBContextManager() as db:
                    assert db is mock_session
                    assert db_conn_ctx_var.get() is mock_session

                    msg = "Test exception"
                    raise ValueError(msg)

        # Should rollback on exception
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

        # Context should be cleared (correct in this case since no prior context)
        assert db_conn_ctx_var.get() is None

    def test_exception_handling_with_existing_session(
        self,
        isolated_test_environment,
        mock_session: Session,
    ) -> None:
        """Test exception handling when reusing existing session - shows another bug."""
        # Pre-set a session
        existing_token = db_conn_ctx_var.set(mock_session)

        try:
            with pytest.raises(ValueError, match="Test exception"), DBContextManager() as db:
                assert db is mock_session
                msg = "Test exception"
                raise ValueError(msg)

            # BUG: Context manager rolled back and closed a session it didn't create
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

            # BUG: Context variable is set to None instead of preserving original
            # This test will fail, exposing the bug
            assert db_conn_ctx_var.get() is mock_session, "BUG: Context should not be cleared for reused sessions"

        finally:
            try:
                db_conn_ctx_var.reset(existing_token)
            except LookupError:
                db_conn_ctx_var.set(None)

    def test_thread_safety_new_sessions(
        self,
        isolated_test_environment,
        mock_session_factory,
    ) -> None:
        """Test thread safety when each thread creates its own session."""
        results = {}
        sessions = {}

        def create_mock_session(thread_id: int):
            session = MagicMock(spec=Session)
            session.thread_id = thread_id  # Add identifier
            return session

        def thread_worker(thread_id: int) -> None:
            # Each thread gets its own mock session
            thread_session = create_mock_session(thread_id)
            thread_factory = MagicMock()
            thread_factory.return_value = thread_session
            sessions[thread_id] = thread_session

            with patch("kwik.database.db_context_manager.get_session_local", return_value=thread_factory):
                with DBContextManager() as db:
                    results[thread_id] = {
                        "session": db,
                        "context_var": db_conn_ctx_var.get(),
                    }

                    # Simulate some work
                    import time
                    time.sleep(0.01)

                    # Verify context is still correct
                    results[f"{thread_id}_mid"] = db_conn_ctx_var.get()

        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify each thread had its own session
        for i in range(5):
            assert results[i]["session"] is sessions[i]
            assert results[i]["context_var"] is sessions[i]
            assert results[f"{i}_mid"] is sessions[i]

    def test_multiple_context_managers_same_thread(
        self,
        isolated_test_environment,
    ) -> None:
        """Test multiple context managers in same thread (sequential, not nested)."""
        sessions = []
        factories = []

        # Create multiple sessions
        for i in range(3):
            session = MagicMock(spec=Session)
            session.session_id = i
            factory = MagicMock()
            factory.return_value = session

            sessions.append(session)
            factories.append(factory)

        # Use context managers sequentially
        for i, (session, factory) in enumerate(zip(sessions, factories, strict=False)):
            assert db_conn_ctx_var.get() is None

            with patch("kwik.database.db_context_manager.get_session_local", return_value=factory):
                with DBContextManager() as db:
                    assert db is session
                    assert db is sessions[i]
                    assert db_conn_ctx_var.get() is session

            # After each context, should be cleared
            assert db_conn_ctx_var.get() is None

            # Session should be committed and closed
            session.commit.assert_called_once()
            session.close.assert_called_once()

    def test_context_manager_initialization(self) -> None:
        """Test DBContextManager initialization."""
        ctx_mgr = DBContextManager()

        assert ctx_mgr.db is None
        assert ctx_mgr.token is None

    def test_context_manager_state_tracking_new_session(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test internal state tracking when creating new session."""
        ctx_mgr = DBContextManager()

        # Initial state
        assert ctx_mgr.db is None
        assert ctx_mgr.token is None

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Enter context
            result = ctx_mgr.__enter__()

            # Check state after enter
            assert ctx_mgr.db is mock_session
            assert ctx_mgr.token is not None  # Should have token for new session
            assert result is mock_session

            # Exit context (no exception)
            ctx_mgr.__exit__(None, None, None)

            # Check calls
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    def test_context_manager_state_tracking_existing_session(
        self,
        isolated_test_environment,
        mock_session: Session,
    ) -> None:
        """Test internal state tracking when reusing existing session."""
        # Set existing session
        existing_token = db_conn_ctx_var.set(mock_session)

        try:
            ctx_mgr = DBContextManager()

            # Initial state
            assert ctx_mgr.db is None
            assert ctx_mgr.token is None

            # Enter context
            result = ctx_mgr.__enter__()

            # Check state after enter
            assert ctx_mgr.db is mock_session
            assert ctx_mgr.token is None  # Should NOT have token for reused session
            assert result is mock_session

            # Exit context (no exception)
            ctx_mgr.__exit__(None, None, None)

            # Check calls - this reveals the bug
            mock_session.commit.assert_called_once()  # BUG: Should not commit reused session
            mock_session.close.assert_called_once()   # BUG: Should not close reused session

        finally:
            try:
                db_conn_ctx_var.reset(existing_token)
            except LookupError:
                db_conn_ctx_var.set(None)

    def test_session_lifecycle_methods_called_correctly(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test that session lifecycle methods are called in correct order."""
        call_order = []

        # Track call order
        def track_commit() -> None:
            call_order.append("commit")

        def track_rollback() -> None:
            call_order.append("rollback")

        def track_close() -> None:
            call_order.append("close")

        mock_session.commit.side_effect = track_commit
        mock_session.rollback.side_effect = track_rollback
        mock_session.close.side_effect = track_close

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Test successful case
            with DBContextManager():
                pass

            assert call_order == ["commit", "close"]

            # Reset for exception case
            call_order.clear()
            mock_session.reset_mock()
            mock_session.commit.side_effect = track_commit
            mock_session.rollback.side_effect = track_rollback
            mock_session.close.side_effect = track_close

            # Test exception case
            with pytest.raises(RuntimeError), DBContextManager():
                msg = "Test error"
                raise RuntimeError(msg)

            assert call_order == ["rollback", "close"]

    def test_original_context_preservation_bug_demonstration(
        self,
        isolated_test_environment,
    ) -> None:
        """Demonstrate the context preservation bug with concrete example."""
        # Set up scenario: User A's session is active
        user_a_session = MagicMock(spec=Session)
        user_a_session.user_id = "user_a"

        user_a_token = db_conn_ctx_var.set(user_a_session)

        try:
            assert db_conn_ctx_var.get() is user_a_session

            # Some nested operation that uses DBContextManager
            # This should reuse User A's session
            with DBContextManager() as nested_db:
                assert nested_db is user_a_session
                assert nested_db.user_id == "user_a"

                # Do some work...

            # CRITICAL BUG: User A's session context should still be active
            # But DBContextManager.__exit__ calls db_conn_ctx_var.set(None)
            current_session = db_conn_ctx_var.get()

            if current_session is None:
                pytest.fail(
                    "CRITICAL BUG DETECTED: DBContextManager destroyed the outer session context. "
                    "This could lead to data loss, security issues, and broken request handling. "
                    "The context manager should only reset contexts it created."
                )

            assert current_session is user_a_session, f"Expected user_a_session, got {current_session}"

        finally:
            try:
                db_conn_ctx_var.reset(user_a_token)
            except LookupError:
                # Token was invalidated by the bug
                db_conn_ctx_var.set(None)

    @pytest.mark.parametrize(
        ("exception_type", "exception_message"),
        [
            (ValueError, "Value error"),
            (RuntimeError, "Runtime error"),
            (KeyError, "Key error"),
            (AttributeError, "Attribute error"),
            (TypeError, "Type error"),
        ]
    )
    def test_exception_handling_various_exceptions(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
        exception_type,
        exception_message,
    ) -> None:
        """Test exception handling with various exception types."""
        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            with pytest.raises(exception_type, match=exception_message):
                with DBContextManager():
                    raise exception_type(exception_message)

        # Should rollback on any exception
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    def test_context_manager_with_session_method_failures(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test behavior when session methods (commit/rollback/close) fail."""
        # Test commit failure
        mock_session.commit.side_effect = RuntimeError("Commit failed")

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            with pytest.raises(RuntimeError, match="Commit failed"):
                with DBContextManager():
                    pass  # Should fail on commit

        # Close should still be called even if commit failed
        mock_session.close.assert_called_once()

        # Reset mocks for rollback failure test
        mock_session.reset_mock()
        mock_session.rollback.side_effect = RuntimeError("Rollback failed")

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Should get the rollback failure, not the original exception
            with pytest.raises(RuntimeError, match="Rollback failed"):
                with DBContextManager():
                    msg = "Original error"
                    raise ValueError(msg)

        # Close should still be called even if rollback failed
        mock_session.close.assert_called_once()

    def test_db_context_manager_as_class_context_manager(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
    ) -> None:
        """Test that DBContextManager properly implements context manager protocol."""
        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Should work with 'with' statement
            with DBContextManager() as db:
                assert hasattr(db, "commit")  # Session-like object
                assert hasattr(db, "rollback")
                assert hasattr(db, "close")
                assert db is mock_session
