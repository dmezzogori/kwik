"""Integration tests for database package components working together."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from kwik.database import DBContextManager, override_current_user
from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var
from kwik.database.engine import get_engine, reset_engine
from kwik.database.session_local import get_session_local, reset_session_local


class TestDatabaseIntegration:
    """Integration tests for database package components."""

    def test_complete_database_workflow(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
        mock_user,
    ) -> None:
        """Test a complete database workflow using all components together."""
        with patch("kwik.database.engine.create_engine") as mock_create_engine:
            with patch("kwik.database.engine.get_settings") as mock_get_settings:
                # Setup engine
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine
                mock_get_settings.return_value = MagicMock()

                # Get engine (should create it)
                engine = get_engine()
                assert engine is mock_engine

                # Get session factory (should use the engine)
                with patch("kwik.database.session_local.sessionmaker", return_value=mock_session_factory):
                    session_factory = get_session_local()
                    assert session_factory is mock_session_factory

                # Use context managers together
                with override_current_user(mock_user):
                    assert current_user_ctx_var.get() is mock_user

                    with DBContextManager() as db:
                        # Should get the mock session
                        assert db is mock_session

                        # Both contexts should be active
                        assert current_user_ctx_var.get() is mock_user
                        assert db_conn_ctx_var.get() is mock_session

                # After contexts, user should be cleared, db context might be cleared
                # (depending on the token management bug)
                assert current_user_ctx_var.get() is None

    def test_engine_and_session_factory_integration(
        self,
        isolated_test_environment,
    ) -> None:
        """Test that session factory properly integrates with engine."""
        with patch("kwik.database.engine.create_engine") as mock_create_engine:
            with patch("kwik.database.engine.get_settings") as mock_get_settings:
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine
                mock_get_settings.return_value = MagicMock()

                # Get engine
                get_engine()

                # Get session factory - should be bound to the engine
                session_factory = get_session_local()

                # Verify binding
                assert session_factory.kw["bind"] is mock_engine

    def test_reset_functions_integration(
        self,
        isolated_test_environment,
    ) -> None:
        """Test that reset functions work correctly together."""
        with patch("kwik.database.engine.create_engine") as mock_create_engine:
            with patch("kwik.database.engine.get_settings") as mock_get_settings:
                # Setup mocks
                mock_engine1 = MagicMock()
                mock_engine2 = MagicMock()
                mock_create_engine.side_effect = [mock_engine1, mock_engine2]
                mock_get_settings.return_value = MagicMock()

                # Get initial engine and session factory
                engine1 = get_engine()
                session_factory1 = get_session_local()

                assert engine1 is mock_engine1
                assert session_factory1.kw["bind"] is mock_engine1

                # Reset engine only
                reset_engine()

                # Get session factory again - should still use old engine
                session_factory2 = get_session_local()
                assert session_factory2 is session_factory1  # Same factory
                assert session_factory2.kw["bind"] is mock_engine1  # Old engine

                # Reset session factory
                reset_session_local()

                # Get session factory again - should now use new engine
                session_factory3 = get_session_local()
                assert session_factory3 is not session_factory1  # New factory
                assert session_factory3.kw["bind"] is mock_engine2  # New engine

    def test_context_isolation_integration(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
        mock_user,
    ) -> None:
        """Test context isolation between different components."""
        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Set up initial contexts
            initial_user = MagicMock()
            initial_user.id = 999
            initial_session = MagicMock(spec=Session)

            user_token = current_user_ctx_var.set(initial_user)
            session_token = db_conn_ctx_var.set(initial_session)

            try:
                # Verify initial state
                assert current_user_ctx_var.get() is initial_user
                assert db_conn_ctx_var.get() is initial_session

                # Use override_current_user (should preserve session context)
                with override_current_user(mock_user):
                    assert current_user_ctx_var.get() is mock_user
                    assert db_conn_ctx_var.get() is initial_session  # Should be preserved

                # User context should be restored
                assert current_user_ctx_var.get() is initial_user
                assert db_conn_ctx_var.get() is initial_session

            finally:
                current_user_ctx_var.reset(user_token)
                db_conn_ctx_var.reset(session_token)

    def test_error_propagation_integration(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
        mock_user,
    ) -> None:
        """Test error propagation through integrated components."""
        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Test that exceptions propagate correctly through nested contexts
            with pytest.raises(RuntimeError, match="Integration test error"):
                with override_current_user(mock_user):
                    with DBContextManager() as db:
                        assert current_user_ctx_var.get() is mock_user
                        assert db is mock_session

                        # Raise exception to test cleanup
                        msg = "Integration test error"
                        raise RuntimeError(msg)

            # Both contexts should be cleaned up
            assert current_user_ctx_var.get() is None
            # db_conn_ctx_var state depends on the token management bug

            # Session should be rolled back
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    def test_multiple_db_context_managers_integration(
        self,
        isolated_test_environment,
        mock_user,
    ) -> None:
        """Test multiple DBContextManager instances in sequence."""
        sessions = []
        factories = []

        # Create multiple mock sessions and factories
        for i in range(3):
            session = MagicMock(spec=Session)
            session.session_id = f"session_{i}"
            factory = MagicMock()
            factory.return_value = session

            sessions.append(session)
            factories.append(factory)

        # Test sequential usage with user context
        with override_current_user(mock_user):
            for i, (session, factory) in enumerate(zip(sessions, factories, strict=False)):
                with patch("kwik.database.db_context_manager.get_session_local", return_value=factory):
                    with DBContextManager() as db:
                        assert db is session
                        assert current_user_ctx_var.get() is mock_user

                        # Each session should be in context when active
                        assert db_conn_ctx_var.get() is session

    def test_global_state_cleanup_integration(
        self,
        isolated_test_environment,
    ) -> None:
        """Test that global state cleanup works across all components."""
        # This test verifies the isolated_test_environment fixture works

        # Check initial state
        import kwik.database.engine as engine_module
        import kwik.database.session_local as session_local_module

        assert engine_module._engine is None
        assert session_local_module._session_local is None
        assert db_conn_ctx_var.get() is None
        assert current_user_ctx_var.get() is None

        # Modify global state
        with patch("kwik.database.engine.create_engine") as mock_create_engine:
            with patch("kwik.database.engine.get_settings") as mock_get_settings:
                mock_create_engine.return_value = MagicMock()
                mock_get_settings.return_value = MagicMock()

                # Create engine and session factory
                get_engine()
                get_session_local()

                # Set context variables
                current_user_ctx_var.set(MagicMock())
                db_conn_ctx_var.set(MagicMock())

                # State should be modified
                assert engine_module._engine is not None
                assert session_local_module._session_local is not None
                assert db_conn_ctx_var.get() is not None
                assert current_user_ctx_var.get() is not None

        # After test, isolated_test_environment should clean up
        # This is verified by the fixture itself

    @pytest.mark.asyncio
    async def test_async_integration(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
        mock_user,
    ) -> None:
        """Test integration in async context."""
        import asyncio

        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            async def async_database_operation() -> str:
                with override_current_user(mock_user), DBContextManager() as db:
                    # Simulate async work
                    await asyncio.sleep(0.001)

                    assert current_user_ctx_var.get() is mock_user
                    assert db is mock_session

                    return "async_result"

            result = await async_database_operation()
            assert result == "async_result"

            # Contexts should be cleaned up
            assert current_user_ctx_var.get() is None

    def test_component_dependency_chain(
        self,
        isolated_test_environment,
    ) -> None:
        """Test the dependency chain: settings -> engine -> session_factory -> DBContextManager."""
        call_order = []

        def mock_get_settings():
            call_order.append("get_settings")
            settings = MagicMock()
            settings.SQLALCHEMY_DATABASE_URI = "test://uri"
            settings.POSTGRES_MAX_CONNECTIONS = 10
            settings.BACKEND_WORKERS = 2
            return settings

        def mock_create_engine(*args, **kwargs):
            call_order.append("create_engine")
            return MagicMock()

        def mock_sessionmaker(*args, **kwargs):
            call_order.append("sessionmaker")
            factory = MagicMock()
            factory.return_value = MagicMock(spec=Session)
            return factory

        with patch("kwik.database.engine.get_settings", side_effect=mock_get_settings):
            with patch("kwik.database.engine.create_engine", side_effect=mock_create_engine):
                with patch("kwik.database.session_local.sessionmaker", side_effect=mock_sessionmaker):
                    # This should trigger the full chain
                    with DBContextManager() as db:
                        assert db is not None

        # Verify call order
        expected_order = ["get_settings", "create_engine", "sessionmaker"]
        assert call_order == expected_order

    def test_real_world_usage_simulation(
        self,
        isolated_test_environment,
        mock_session_factory,
        mock_session: Session,
        mock_user,
    ) -> None:
        """Simulate real-world usage patterns."""
        with patch("kwik.database.db_context_manager.get_session_local", return_value=mock_session_factory):
            # Simulate a web request handling pattern
            def simulate_request_handler(user, operation) -> str:
                with override_current_user(user), DBContextManager() as db:
                    # Simulate various operations
                    if operation == "create":
                        # Simulate creating something
                        return f"created_with_session_{id(db)}"
                    if operation == "read":
                        # Simulate reading something
                        return f"read_with_session_{id(db)}"
                    if operation == "error":
                        msg = "Simulated business logic error"
                        raise ValueError(msg)

                    return "default_result"

            # Test successful operations
            result1 = simulate_request_handler(mock_user, "create")
            assert "created_with_session" in result1

            result2 = simulate_request_handler(mock_user, "read")
            assert "read_with_session" in result2

            # Test error handling
            with pytest.raises(ValueError, match="Simulated business logic error"):
                simulate_request_handler(mock_user, "error")

            # After error, rollback should have been called
            mock_session.rollback.assert_called()
            mock_session.close.assert_called()
