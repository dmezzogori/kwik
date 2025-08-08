"""Local database session factory configuration."""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from .engine import get_engine

# Cache for lazily initialized session factories
_session_local: sessionmaker | None = None


def get_session_local() -> sessionmaker:
    """Get the main session factory, creating it lazily on first access."""
    global _session_local  # noqa: PLW0603
    if _session_local is None:
        _session_local = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            expire_on_commit=False,  # Modern default for better performance
        )
    return _session_local


def reset_session_local() -> None:
    """Reset cached session factory to force recreation with new engine."""
    global _session_local  # noqa: PLW0603
    _session_local = None
