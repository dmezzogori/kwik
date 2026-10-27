"""
Session-aware authentication for kwik.

kwik defines the session record, the store protocol an application implements to persist
it, an in-memory store, and the service that opens, refreshes and revokes sessions. The
application owns the session table; kwik adds none.
"""

from __future__ import annotations

from .memory import InMemoryAuthSessionStore
from .service import open_session, refresh_session, require_active_session, revoke_session
from .store import AuthSession, AuthSessionStore

__all__ = [
    "AuthSession",
    "AuthSessionStore",
    "InMemoryAuthSessionStore",
    "open_session",
    "refresh_session",
    "require_active_session",
    "revoke_session",
]
