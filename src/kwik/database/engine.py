"""Database engine configuration for SQLAlchemy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine

from kwik.core.settings import get_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# Cache for lazily initialized engines
_engine: Engine | None = None
_alternate_engine: Engine | None = None


def get_engine() -> Engine:
    """Get the main database engine, creating it lazily on first access."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            url=settings.SQLALCHEMY_DATABASE_URI,
            pool_pre_ping=True,
            pool_size=settings.POSTGRES_MAX_CONNECTIONS // settings.BACKEND_WORKERS,
            max_overflow=0,
        )
    return _engine


def get_alternate_engine() -> Engine | None:
    """Get the alternate database engine, creating it lazily on first access."""
    global _alternate_engine  # noqa: PLW0603
    if _alternate_engine is None:
        settings = get_settings()
        if settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI is not None:
            _alternate_engine = create_engine(url=settings.alternate_db.ALTERNATE_SQLALCHEMY_DATABASE_URI)
    return _alternate_engine


def reset_engines() -> None:
    """Reset cached engines to force recreation with new settings."""
    global _engine, _alternate_engine  # noqa: PLW0603
    _engine = None
    _alternate_engine = None


# Backward compatibility: provide engine and alternate_engine as module-level attributes
# These will be created lazily when first accessed
def __getattr__(name: str) -> Engine | None:
    """Provide backward compatibility for direct access to engine attributes."""
    if name == "engine":
        return get_engine()
    if name == "alternate_engine":
        return get_alternate_engine()
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
