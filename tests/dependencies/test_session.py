"""Tests for session dependency injection."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from kwik.dependencies.session import _get_session

if TYPE_CHECKING:
    from collections.abc import Generator


class TestGetSession:
    """Test cases for the _get_session function."""

    def test_get_session_happy_path(self) -> None:
        """Test successful session creation and yielding."""
        # Arrange
        mock_session = MagicMock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        # Create a mock session_scope that yields the session
        @contextmanager
        def mock_session_scope(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:  # noqa: ARG001
            yield session

        with patch("kwik.dependencies.session.session_scope", side_effect=mock_session_scope):
            # Act
            generator = _get_session(mock_request)
            result = next(generator)

            # Assert
            assert result is mock_session
            mock_session_local.assert_called_once()

    def test_get_session_calls_session_scope_with_commit_true(self) -> None:
        """Test that session_scope is called with commit=True."""
        # Arrange
        mock_session = MagicMock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        with patch("kwik.dependencies.session.session_scope") as mock_session_scope:
            # Create a mock context manager
            @contextmanager
            def mock_context_manager(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:  # noqa: ARG001
                yield session

            mock_session_scope.side_effect = mock_context_manager

            # Act
            generator = _get_session(mock_request)
            next(generator)

            # Assert
            mock_session_scope.assert_called_once_with(session=mock_session, commit=True)

    def test_get_session_accesses_request_app_state(self) -> None:
        """Test that the function accesses request.app.state.SessionLocal."""
        # Arrange
        mock_session = MagicMock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        @contextmanager
        def mock_session_scope(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:  # noqa: ARG001
            yield session

        with patch("kwik.dependencies.session.session_scope", side_effect=mock_session_scope):
            # Act
            generator = _get_session(mock_request)
            next(generator)

            # Assert - verify that SessionLocal was accessed and called
            assert mock_request.app.state.SessionLocal is mock_session_local
            mock_session_local.assert_called_once()

    def test_get_session_missing_session_local_attribute_error(self) -> None:
        """Test behavior when request.app.state.SessionLocal is missing."""
        # Arrange
        mock_request = Mock()
        del mock_request.app.state.SessionLocal  # Remove the attribute

        # Act & Assert
        with pytest.raises(AttributeError):
            list(_get_session(mock_request))

    def test_get_session_session_local_call_raises_exception(self) -> None:
        """Test behavior when SessionLocal() call raises an exception."""
        # Arrange
        mock_session_local = Mock(side_effect=RuntimeError("Database connection failed"))
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        # Act & Assert
        with pytest.raises(RuntimeError, match="Database connection failed"):
            list(_get_session(mock_request))

    def test_get_session_session_scope_exception_propagates(self) -> None:
        """Test that exceptions from session_scope are propagated."""
        # Arrange
        mock_session = MagicMock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        @contextmanager
        def failing_session_scope(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:  # noqa: ARG001
            msg = "Session scope failed"
            raise RuntimeError(msg)
            yield  # pragma: no cover - unreachable after raise

        with (
            patch("kwik.dependencies.session.session_scope", side_effect=failing_session_scope),
            pytest.raises(RuntimeError, match="Session scope failed"),
        ):
            list(_get_session(mock_request))

    def test_get_session_is_generator(self) -> None:
        """Test that _get_session returns a generator."""
        # Arrange
        mock_session = MagicMock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        @contextmanager
        def mock_session_scope(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:  # noqa: ARG001
            yield session

        with patch("kwik.dependencies.session.session_scope", side_effect=mock_session_scope):
            # Act
            result = _get_session(mock_request)

            # Assert
            assert hasattr(result, "__next__")
            assert hasattr(result, "__iter__")

    def test_get_session_generator_single_yield(self) -> None:
        """Test that the generator yields exactly once."""
        # Arrange
        mock_session = MagicMock(spec=Session)
        mock_session_local = Mock(return_value=mock_session)
        mock_request = Mock()
        mock_request.app.state.SessionLocal = mock_session_local

        @contextmanager
        def mock_session_scope(*, session: Session, commit: bool = False) -> Generator[Session, None, None]:  # noqa: ARG001
            yield session

        with patch("kwik.dependencies.session.session_scope", side_effect=mock_session_scope):
            # Act
            generator = _get_session(mock_request)
            first_yield = next(generator)

            # Assert first yield works
            assert first_yield is mock_session

            # Assert second call raises StopIteration
            with pytest.raises(StopIteration):
                next(generator)
