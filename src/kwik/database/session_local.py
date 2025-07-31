"""Local database session factory configuration."""

from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from kwik.database.engine import get_alternate_engine, get_engine

# Cache for lazily initialized session factories
_session_local: sessionmaker | None = None
_alternate_session_local: sessionmaker | None = None


def get_session_local() -> sessionmaker:
    """Get the main session factory, creating it lazily on first access."""
    global _session_local  # noqa: PLW0603
    if _session_local is None:
        _session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _session_local


def get_alternate_session_local() -> sessionmaker | None:
    """Get the alternate session factory, creating it lazily on first access."""
    global _alternate_session_local  # noqa: PLW0603
    if _alternate_session_local is None:
        alternate_engine = get_alternate_engine()
        if alternate_engine is not None:
            _alternate_session_local = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=alternate_engine,
            )
    return _alternate_session_local


def reset_session_locals() -> None:
    """Reset cached session factories to force recreation with new engines."""
    global _session_local, _alternate_session_local  # noqa: PLW0603
    _session_local = None
    _alternate_session_local = None


# Backward compatibility: provide SessionLocal and AlternateSessionLocal as module-level attributes
def __getattr__(name: str) -> sessionmaker | None:
    """Provide backward compatibility for direct access to session factory attributes."""
    if name == "SessionLocal":
        return get_session_local()
    if name == "AlternateSessionLocal":
        return get_alternate_session_local()
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
