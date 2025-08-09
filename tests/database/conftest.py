"""Database-specific pytest fixtures for unit testing database package components."""

from __future__ import annotations

import contextlib
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def clean_global_state() -> Generator[None, None, None]:
    """Ensure clean global state for engine and session_local between tests."""
    # Import here to avoid circular imports during test collection
    from kwik.database.engine import reset_engine
    from kwik.database.session_local import reset_session_local

    # Reset globals before test
    reset_engine()
    reset_session_local()
    yield
    # Reset globals after test to prevent interference
    reset_engine()
    reset_session_local()


@pytest.fixture
def clean_context_vars() -> Generator[None, None, None]:
    """Ensure clean context variables between tests."""
    from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var

    # Store original values
    original_db_conn = db_conn_ctx_var.get(None)
    original_current_user = current_user_ctx_var.get(None)

    # Reset to default
    db_conn_ctx_var.set(None)
    current_user_ctx_var.set(None)

    yield

    # Restore original values
    db_conn_ctx_var.set(original_db_conn)
    current_user_ctx_var.set(original_current_user)


@pytest.fixture
def mock_settings() -> MagicMock:
    """Mock settings for database configuration tests."""
    mock_settings = MagicMock()
    mock_settings.SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://test:test@localhost/test_db"
    mock_settings.POSTGRES_MAX_CONNECTIONS = 20
    mock_settings.BACKEND_WORKERS = 2
    return mock_settings


@pytest.fixture
def mock_engine() -> MagicMock:
    """Mock SQLAlchemy engine for unit testing."""
    return MagicMock(spec=Engine)


@pytest.fixture
def mock_session() -> MagicMock:
    """Mock SQLAlchemy session for unit testing."""
    mock_session = MagicMock(spec=Session)
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    return mock_session


@pytest.fixture
def mock_session_factory(mock_session: Session) -> MagicMock:
    """Mock sessionmaker that returns the mock_session."""
    mock_sessionmaker = MagicMock(spec=sessionmaker)
    mock_sessionmaker.return_value = mock_session
    return mock_sessionmaker


@pytest.fixture
def mock_user() -> MagicMock:
    """Mock User object for context variable testing."""
    mock_user = MagicMock()
    mock_user.id = 123
    mock_user.email = "test@example.com"
    mock_user.name = "Test User"
    return mock_user


@pytest.fixture
def isolated_test_environment(clean_global_state, clean_context_vars) -> None:
    """Combined fixture providing completely isolated test environment."""
    return


@pytest.fixture
def context_token_tracker():
    """Helper fixture to track context variable tokens for testing."""
    tokens = []

    @contextmanager
    def track_token(ctx_var, value):
        token = ctx_var.set(value)
        tokens.append((ctx_var, token))
        try:
            yield token
        finally:
            ctx_var.reset(token)

    yield track_token

    # Clean up any remaining tokens
    for ctx_var, token in tokens:
        with contextlib.suppress(LookupError, ValueError):
            ctx_var.reset(token)  # Token might already be reset, ignore
