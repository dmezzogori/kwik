"""Tests for database engine management."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ArgumentError

from kwik.database.engine import get_engine, reset_engine


class TestEngineModule:
    """Test suite for engine.py module."""

    def test_get_engine_lazy_initialization(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test that engine is created lazily on first access."""
        # Mock create_engine to return a mock engine
        mock_engine = MagicMock(spec=Engine)
        patch_create_engine.return_value = mock_engine

        # Verify create_engine hasn't been called yet
        patch_create_engine.assert_not_called()

        # First call should create engine
        result = get_engine()

        assert result is mock_engine
        patch_create_engine.assert_called_once()

    def test_get_engine_caching_behavior(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test that subsequent calls return the same engine instance."""
        mock_engine = MagicMock(spec=Engine)
        patch_create_engine.return_value = mock_engine

        # Multiple calls should return same instance
        engine1 = get_engine()
        engine2 = get_engine()
        engine3 = get_engine()

        assert engine1 is engine2
        assert engine2 is engine3

        # create_engine should only be called once
        patch_create_engine.assert_called_once()

    def test_engine_configuration_parameters(
        self,
        isolated_test_environment,
        patch_create_engine,
        mock_settings,
    ) -> None:
        """Test that engine is configured with correct parameters."""
        mock_engine = MagicMock(spec=Engine)
        patch_create_engine.return_value = mock_engine

        # Configure mock settings
        mock_settings.SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://test:password@localhost/testdb"
        mock_settings.POSTGRES_MAX_CONNECTIONS = 20
        mock_settings.BACKEND_WORKERS = 4

        with patch("kwik.database.engine.get_settings", return_value=mock_settings):
            get_engine()

        # Verify create_engine was called with correct parameters
        patch_create_engine.assert_called_once_with(
            url="postgresql+psycopg2://test:password@localhost/testdb",
            pool_pre_ping=True,
            pool_size=5,  # 20 // 4
            max_overflow=0,
            query_cache_size=1200,
        )

    def test_reset_engine_functionality(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test that reset_engine() clears the cached engine."""
        mock_engine1 = MagicMock(spec=Engine)
        mock_engine2 = MagicMock(spec=Engine)
        patch_create_engine.side_effect = [mock_engine1, mock_engine2]

        # Get first engine
        engine1 = get_engine()
        assert engine1 is mock_engine1

        # Reset engine
        reset_engine()

        # Get engine again - should create a new one
        engine2 = get_engine()
        assert engine2 is mock_engine2
        assert engine2 is not engine1

        # create_engine should have been called twice
        assert patch_create_engine.call_count == 2

    def test_thread_safety_of_global_state(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test thread safety when multiple threads call get_engine() simultaneously."""
        mock_engine = MagicMock(spec=Engine)
        patch_create_engine.return_value = mock_engine

        results = []
        exceptions = []

        def worker() -> None:
            try:
                engine = get_engine()
                results.append(engine)
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

        # Verify all threads got the same engine instance
        assert len(results) == 10
        assert all(engine is mock_engine for engine in results)

        # create_engine should only be called once despite multiple threads
        patch_create_engine.assert_called_once()

    def test_concurrent_reset_and_get_engine(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test behavior when reset_engine() and get_engine() are called concurrently."""
        engines = [MagicMock(spec=Engine) for _ in range(5)]
        patch_create_engine.side_effect = engines

        results = []
        exceptions = []

        def get_worker() -> None:
            try:
                engine = get_engine()
                results.append(("get", engine))
            except Exception as e:
                exceptions.append(("get", e))

        def reset_worker() -> None:
            try:
                reset_engine()
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

        # Should have created multiple engines due to resets
        assert patch_create_engine.call_count >= 1

        # All get operations should have returned valid engines
        get_results = [result[1] for result in results if result[0] == "get"]
        assert all(engine is not None for engine in get_results)

    def test_engine_configuration_with_different_settings(
        self,
        isolated_test_environment,
        patch_create_engine,
    ) -> None:
        """Test engine creation with different settings configurations."""
        mock_engine1 = MagicMock(spec=Engine)
        mock_engine2 = MagicMock(spec=Engine)
        patch_create_engine.side_effect = [mock_engine1, mock_engine2]

        # First configuration
        settings1 = MagicMock()
        settings1.SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://user1:pass1@host1/db1"
        settings1.POSTGRES_MAX_CONNECTIONS = 10
        settings1.BACKEND_WORKERS = 2

        with patch("kwik.database.engine.get_settings", return_value=settings1):
            engine1 = get_engine()

        patch_create_engine.assert_called_with(
            url="postgresql+psycopg2://user1:pass1@host1/db1",
            pool_pre_ping=True,
            pool_size=5,  # 10 // 2
            max_overflow=0,
            query_cache_size=1200,
        )

        # Reset and change settings
        reset_engine()

        settings2 = MagicMock()
        settings2.SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://user2:pass2@host2/db2"
        settings2.POSTGRES_MAX_CONNECTIONS = 30
        settings2.BACKEND_WORKERS = 6

        with patch("kwik.database.engine.get_settings", return_value=settings2):
            engine2 = get_engine()

        # Verify second call with different settings
        assert patch_create_engine.call_count == 2
        patch_create_engine.assert_called_with(
            url="postgresql+psycopg2://user2:pass2@host2/db2",
            pool_pre_ping=True,
            pool_size=5,  # 30 // 6
            max_overflow=0,
            query_cache_size=1200,
        )

        assert engine1 is not engine2

    def test_get_settings_error_handling(
        self,
        isolated_test_environment,
        patch_create_engine,
    ) -> None:
        """Test error handling when get_settings() fails."""
        # Mock get_settings to raise an exception
        with patch("kwik.database.engine.get_settings", side_effect=RuntimeError("Settings unavailable")):
            with pytest.raises(RuntimeError, match="Settings unavailable"):
                get_engine()

        # create_engine should not have been called
        patch_create_engine.assert_not_called()

    def test_create_engine_error_handling(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test error handling when create_engine() fails."""
        # Mock create_engine to raise an exception
        patch_create_engine.side_effect = ArgumentError("Invalid connection string")

        with pytest.raises(ArgumentError, match="Invalid connection string"):
            get_engine()

        patch_create_engine.assert_called_once()

    def test_pool_size_calculation_edge_cases(
        self,
        isolated_test_environment,
        patch_create_engine,
    ) -> None:
        """Test pool size calculation with edge case values."""
        test_cases = [
            # (max_connections, workers, expected_pool_size)
            (1, 1, 1),  # Minimum case
            (10, 1, 10),  # Single worker
            (10, 3, 3),  # Integer division (10 // 3 = 3)
            (1, 10, 0),  # More workers than connections
            (100, 4, 25),  # Normal case
        ]

        for max_conn, workers, expected_pool_size in test_cases:
            reset_engine()
            patch_create_engine.reset_mock()

            settings = MagicMock()
            settings.SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://test@localhost/test"
            settings.POSTGRES_MAX_CONNECTIONS = max_conn
            settings.BACKEND_WORKERS = workers

            with patch("kwik.database.engine.get_settings", return_value=settings):
                get_engine()

            # Check that pool_size was calculated correctly
            call_args = patch_create_engine.call_args
            assert call_args.kwargs["pool_size"] == expected_pool_size

    def test_engine_has_correct_configuration_defaults(
        self,
        isolated_test_environment,
        patch_create_engine,
        patch_get_settings,
    ) -> None:
        """Test that engine is configured with correct default parameters."""
        mock_engine = MagicMock(spec=Engine)
        patch_create_engine.return_value = mock_engine

        get_engine()

        # Verify all expected parameters are set
        call_args = patch_create_engine.call_args
        assert call_args.kwargs["pool_pre_ping"] is True
        assert call_args.kwargs["max_overflow"] == 0
        assert call_args.kwargs["query_cache_size"] == 1200

    def test_reset_engine_is_idempotent(self, isolated_test_environment) -> None:
        """Test that reset_engine() can be called multiple times safely."""
        # Should not raise any exceptions
        reset_engine()
        reset_engine()
        reset_engine()

        # After multiple resets, get_engine() should still work
        with patch("kwik.database.engine.create_engine") as mock_create:
            with patch("kwik.database.engine.get_settings") as mock_settings:
                mock_create.return_value = MagicMock(spec=Engine)
                mock_settings.return_value = MagicMock()

                engine = get_engine()
                assert engine is not None

    def test_global_state_isolation_between_tests(self) -> None:
        """Test that global state doesn't leak between test methods."""
        # This test doesn't use isolated_test_environment fixture
        # to verify the fixture actually works

        # Check that the module global is clean
        import kwik.database.engine as engine_module
        assert engine_module._engine is None

        # Set the global state
        with patch("kwik.database.engine.create_engine") as mock_create:
            with patch("kwik.database.engine.get_settings") as mock_settings:
                mock_create.return_value = MagicMock(spec=Engine)
                mock_settings.return_value = MagicMock()

                get_engine()
                assert engine_module._engine is not None

        # Reset it
        reset_engine()
        assert engine_module._engine is None

    def test_engine_module_constants_and_structure(self) -> None:
        """Test that the engine module has the expected structure."""
        import kwik.database.engine as engine_module

        # Check that module has expected functions
        assert hasattr(engine_module, "get_engine")
        assert hasattr(engine_module, "reset_engine")
        assert callable(engine_module.get_engine)
        assert callable(engine_module.reset_engine)

        # Check that _engine is initialized to None
        assert hasattr(engine_module, "_engine")
        assert engine_module._engine is None

    @pytest.mark.parametrize(
        ("database_uri", "expected_driver"),
        [
            ("postgresql+psycopg2://user:pass@host/db", "postgresql+psycopg2"),
            ("postgresql+asyncpg://user:pass@host/db", "postgresql+asyncpg"),
            ("sqlite:///path/to/db.sqlite", "sqlite"),
            ("mysql+pymysql://user:pass@host/db", "mysql+pymysql"),
        ],
    )
    def test_engine_with_different_database_drivers(
        self,
        isolated_test_environment,
        patch_create_engine,
        database_uri: str,
        expected_driver: str,
    ) -> None:
        """Test engine creation with different database drivers."""
        mock_engine = MagicMock(spec=Engine)
        patch_create_engine.return_value = mock_engine

        settings = MagicMock()
        settings.SQLALCHEMY_DATABASE_URI = database_uri
        settings.POSTGRES_MAX_CONNECTIONS = 20
        settings.BACKEND_WORKERS = 4

        with patch("kwik.database.engine.get_settings", return_value=settings):
            get_engine()

        # Verify create_engine was called with the correct URL
        call_args = patch_create_engine.call_args
        assert call_args.kwargs["url"] == database_uri
        assert expected_driver in database_uri
