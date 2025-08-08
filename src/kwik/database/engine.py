"""Database engine configuration for SQLAlchemy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from kwik.core.settings import get_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# Cache for lazily initialized engines
_engine: Engine | None = None


def get_engine() -> Engine:
    """Get the database engine, creating it lazily on first access."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            url=settings.SQLALCHEMY_DATABASE_URI,
            pool_pre_ping=True,
            pool_size=settings.POSTGRES_MAX_CONNECTIONS // settings.BACKEND_WORKERS,
            max_overflow=0,
            # Modern SQLAlchemy 2.0 optimizations
            query_cache_size=1200,  # Enable query compilation caching for better performance
        )
    return _engine


def reset_engine() -> None:
    """Reset cached engine to force recreation with new settings."""
    global _engine  # noqa: PLW0603
    _engine = None
