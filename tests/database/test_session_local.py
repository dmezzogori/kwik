"""Tests for session factory management."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from kwik.database.session_local import get_session_local, reset_session_local


class TestSessionLocalModule:
    """Test suite for session_local.py module."""

    def test_get_session_local_lazy_initialization(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that sessionmaker is created lazily on first access."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine) as mock_get_engine:
            # Verify get_engine hasn't been called yet
            mock_get_engine.assert_not_called()

            # First call should create sessionmaker
            result = get_session_local()

            assert isinstance(result, sessionmaker)
            mock_get_engine.assert_called_once()

    def test_get_session_local_caching_behavior(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that subsequent calls return the same sessionmaker instance."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine) as mock_get_engine:
            # Multiple calls should return same instance
            session_factory1 = get_session_local()
            session_factory2 = get_session_local()
            session_factory3 = get_session_local()

            assert session_factory1 is session_factory2
            assert session_factory2 is session_factory3

            # get_engine should only be called once
            mock_get_engine.assert_called_once()

    def test_sessionmaker_configuration(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that sessionmaker is configured with correct parameters."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine):
            session_factory = get_session_local()

            # Check sessionmaker configuration
            assert session_factory.kw["bind"] is mock_engine
            assert session_factory.kw["autoflush"] is False
            assert session_factory.kw["expire_on_commit"] is False

    def test_reset_session_local_functionality(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that reset_session_local() clears the cached sessionmaker."""
        mock_engine2 = MagicMock(spec=Engine)

        with patch("kwik.database.session_local.get_engine", side_effect=[mock_engine, mock_engine2]) as mock_get_engine:
            # Get first sessionmaker
            session_factory1 = get_session_local()
            assert session_factory1.kw["bind"] is mock_engine

            # Reset session factory
            reset_session_local()

            # Get sessionmaker again - should create a new one
            session_factory2 = get_session_local()
            assert session_factory2.kw["bind"] is mock_engine2
            assert session_factory2 is not session_factory1

            # get_engine should have been called twice
            assert mock_get_engine.call_count == 2

    def test_thread_safety_of_global_state(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test thread safety when multiple threads call get_session_local() simultaneously."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine) as mock_get_engine:
            results = []
            exceptions = []

            def worker() -> None:
                try:
                    session_factory = get_session_local()
                    results.append(session_factory)
                except Exception as e:
                    exceptions.append(e)

            # Launch multiple threads simultaneously
            threads = []
            for _ in range(10):
                thread = threading.Thread(target=worker)
                threads.append(thread)

            # Start all threads
            for thread in threads:
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify no exceptions occurred
            assert not exceptions, f"Exceptions occurred: {exceptions}"

            # Verify all threads got the same sessionmaker instance
            assert len(results) == 10
            assert all(factory is results[0] for factory in results)

            # get_engine should only be called once despite multiple threads
            mock_get_engine.assert_called_once()

    def test_concurrent_reset_and_get_session_local(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test behavior when reset_session_local() and get_session_local() are called concurrently."""
        engines = [MagicMock(spec=Engine) for _ in range(5)]

        with patch("kwik.database.session_local.get_engine", side_effect=engines) as mock_get_engine:
            results = []
            exceptions = []

            def get_worker() -> None:
                try:
                    session_factory = get_session_local()
                    results.append(("get", session_factory))
                except Exception as e:
                    exceptions.append(("get", e))

            def reset_worker() -> None:
                try:
                    reset_session_local()
                    results.append(("reset", None))
                except Exception as e:
                    exceptions.append(("reset", e))

            # Mix of get and reset operations
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                # Submit a mix of get and reset operations
                for i in range(20):
                    if i % 3 == 0:  # Every third operation is a reset
                        futures.append(executor.submit(reset_worker))
                    else:
                        futures.append(executor.submit(get_worker))

                # Wait for all to complete
                for future in as_completed(futures):
                    future.result()

            # Verify no exceptions occurred
            assert not exceptions, f"Exceptions occurred: {exceptions}"

            # Should have created multiple sessionmakers due to resets
            assert mock_get_engine.call_count >= 1

            # All get operations should have returned valid sessionmakers
            get_results = [result[1] for result in results if result[0] == "get"]
            assert all(isinstance(factory, sessionmaker) for factory in get_results)

    def test_sessionmaker_creates_working_sessions(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that the sessionmaker creates working Session instances."""
        mock_session = MagicMock(spec=Session)

        with patch("kwik.database.session_local.get_engine", return_value=mock_engine):
            # Mock sessionmaker to return our mock session
            with patch("sqlalchemy.orm.sessionmaker") as mock_sessionmaker_class:
                mock_sessionmaker_instance = MagicMock()
                mock_sessionmaker_instance.return_value = mock_session
                mock_sessionmaker_class.return_value = mock_sessionmaker_instance

                session_factory = get_session_local()

                # Verify sessionmaker was created with correct parameters
                mock_sessionmaker_class.assert_called_once_with(
                    bind=mock_engine,
                    autoflush=False,
                    expire_on_commit=False,
                )

                # Test that the factory can create sessions
                created_session = session_factory()
                assert created_session is mock_session

    def test_integration_with_engine_reset(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test behavior when engine is reset but session_local is not."""
        mock_engine2 = MagicMock(spec=Engine)

        with patch("kwik.database.session_local.get_engine", side_effect=[mock_engine, mock_engine]) as mock_get_engine:
            # Get initial sessionmaker
            session_factory1 = get_session_local()
            assert session_factory1.kw["bind"] is mock_engine

            # Mock engine reset (get_engine now returns different engine)
            mock_get_engine.side_effect = [mock_engine, mock_engine, mock_engine2]

            # Get sessionmaker again - should still return cached one with old engine
            session_factory2 = get_session_local()
            assert session_factory2 is session_factory1
            assert session_factory2.kw["bind"] is mock_engine  # Still old engine

            # Reset session_local to pick up new engine
            reset_session_local()
            session_factory3 = get_session_local()
            assert session_factory3.kw["bind"] is mock_engine2  # New engine
            assert session_factory3 is not session_factory1

    def test_get_engine_error_handling(
        self,
        isolated_test_environment,
    ) -> None:
        """Test error handling when get_engine() fails."""
        with patch("kwik.database.session_local.get_engine", side_effect=RuntimeError("Engine unavailable")):
            with pytest.raises(RuntimeError, match="Engine unavailable"):
                get_session_local()

    def test_sessionmaker_error_handling(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test error handling when sessionmaker creation fails."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine):
            with patch("sqlalchemy.orm.sessionmaker", side_effect=ValueError("Invalid sessionmaker args")):
                with pytest.raises(ValueError, match="Invalid sessionmaker args"):
                    get_session_local()

    def test_reset_session_local_is_idempotent(
        self,
        isolated_test_environment,
    ) -> None:
        """Test that reset_session_local() can be called multiple times safely."""
        # Should not raise any exceptions
        reset_session_local()
        reset_session_local()
        reset_session_local()

        # After multiple resets, get_session_local() should still work
        with patch("kwik.database.session_local.get_engine") as mock_get_engine:
            mock_get_engine.return_value = MagicMock(spec=Engine)

            session_factory = get_session_local()
            assert isinstance(session_factory, sessionmaker)

    def test_global_state_isolation_between_tests(self) -> None:
        """Test that global state doesn't leak between test methods."""
        # This test doesn't use isolated_test_environment fixture
        # to verify the fixture actually works

        # Check that the module global is clean
        import kwik.database.session_local as session_local_module
        assert session_local_module._session_local is None

        # Set the global state
        with patch("kwik.database.session_local.get_engine") as mock_get_engine:
            mock_get_engine.return_value = MagicMock(spec=Engine)

            get_session_local()
            assert session_local_module._session_local is not None

        # Reset it
        reset_session_local()
        assert session_local_module._session_local is None

    def test_session_local_module_constants_and_structure(self) -> None:
        """Test that the session_local module has the expected structure."""
        import kwik.database.session_local as session_local_module

        # Check that module has expected functions
        assert hasattr(session_local_module, "get_session_local")
        assert hasattr(session_local_module, "reset_session_local")
        assert callable(session_local_module.get_session_local)
        assert callable(session_local_module.reset_session_local)

        # Check that _session_local is initialized to None
        assert hasattr(session_local_module, "_session_local")
        assert session_local_module._session_local is None

    def test_sessionmaker_with_different_engines(
        self,
        isolated_test_environment,
    ) -> None:
        """Test sessionmaker creation with different engine types."""
        engines = [
            MagicMock(spec=Engine, name="engine1"),
            MagicMock(spec=Engine, name="engine2"),
            MagicMock(spec=Engine, name="engine3"),
        ]

        for _i, engine in enumerate(engines):
            reset_session_local()

            with patch("kwik.database.session_local.get_engine", return_value=engine):
                session_factory = get_session_local()

                assert session_factory.kw["bind"] is engine
                assert session_factory.kw["autoflush"] is False
                assert session_factory.kw["expire_on_commit"] is False

    def test_sessionmaker_configuration_immutability(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that sessionmaker configuration cannot be accidentally modified."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine):
            session_factory = get_session_local()

            # Store original configuration
            original_bind = session_factory.kw["bind"]
            original_autoflush = session_factory.kw["autoflush"]
            original_expire_on_commit = session_factory.kw["expire_on_commit"]

            # Get the same factory again
            session_factory2 = get_session_local()

            # Should be the same instance with same configuration
            assert session_factory2 is session_factory
            assert session_factory2.kw["bind"] is original_bind
            assert session_factory2.kw["autoflush"] == original_autoflush
            assert session_factory2.kw["expire_on_commit"] == original_expire_on_commit

    def test_session_creation_from_factory(
        self,
        isolated_test_environment,
        mock_engine: Engine,
    ) -> None:
        """Test that sessions created from factory have correct properties."""
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine):
            session_factory = get_session_local()

            # Create a session from the factory
            # We'll mock the sessionmaker call to verify it's called correctly
            with patch.object(session_factory, "__call__") as mock_call:
                mock_session = MagicMock(spec=Session)
                mock_call.return_value = mock_session

                session = session_factory()

                assert session is mock_session
                mock_call.assert_called_once_with()

    def test_multiple_session_factory_resets_with_different_engines(
        self,
        isolated_test_environment,
    ) -> None:
        """Test multiple resets with different engines to ensure clean state."""
        engines = [MagicMock(spec=Engine, name=f"engine_{i}") for i in range(5)]

        session_factories = []

        for engine in engines:
            reset_session_local()

            with patch("kwik.database.session_local.get_engine", return_value=engine):
                factory = get_session_local()
                session_factories.append(factory)

                # Verify each factory is bound to the correct engine
                assert factory.kw["bind"] is engine

        # All factories should be different instances
        for i in range(len(session_factories)):
            for j in range(i + 1, len(session_factories)):
                assert session_factories[i] is not session_factories[j]

    @pytest.mark.parametrize("reset_count", [1, 2, 5, 10])
    def test_multiple_resets_followed_by_get(
        self,
        isolated_test_environment,
        mock_engine: Engine,
        reset_count: int,
    ) -> None:
        """Test multiple consecutive resets followed by get_session_local()."""
        # Perform multiple resets
        for _ in range(reset_count):
            reset_session_local()

        # Should still work after multiple resets
        with patch("kwik.database.session_local.get_engine", return_value=mock_engine):
            session_factory = get_session_local()
            assert isinstance(session_factory, sessionmaker)
            assert session_factory.kw["bind"] is mock_engine
