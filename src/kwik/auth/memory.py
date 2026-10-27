"""An in-memory auth session store for tests and single-process applications."""

from __future__ import annotations

import threading
from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from .store import AuthSession


class InMemoryAuthSessionStore:
    """
    A dict-backed :class:`~kwik.auth.AuthSessionStore`, keyed by session id.

    State lives in one process and is lost on restart, so it suits tests and single-process
    applications only. Records are copied in and out, so callers cannot change stored state
    except through the store's methods, and every method runs under one lock, which makes
    :meth:`rotate` a true compare-and-set.
    """

    def __init__(self) -> None:
        """Create an empty store."""
        self._sessions: dict[str, AuthSession] = {}
        self._lock = threading.Lock()

    def create(self, session: AuthSession) -> None:
        """Store a copy of ``session`` under its id."""
        with self._lock:
            self._sessions[session.id] = replace(session)

    def get(self, session_id: str) -> AuthSession | None:
        """Return a copy of the record with ``session_id``, or None."""
        with self._lock:
            record = self._sessions.get(session_id)
            return None if record is None else replace(record)

    def update(self, session: AuthSession) -> None:
        """Replace the stored record with a copy of ``session``."""
        with self._lock:
            self._sessions[session.id] = replace(session)

    def rotate(
        self,
        session_id: str,
        *,
        expected_token_id: str,
        new_token_id: str,
        expires_at: datetime,
        rotated_at: datetime,
    ) -> AuthSession | None:
        """Install ``new_token_id`` only if the current refresh token id is ``expected_token_id``."""
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None or record.refresh_token_id != expected_token_id:
                return None
            rotated = replace(
                record,
                previous_refresh_token_id=expected_token_id,
                refresh_token_id=new_token_id,
                expires_at=expires_at,
                rotated_at=rotated_at,
            )
            self._sessions[session_id] = rotated
            return replace(rotated)

    def revoke(self, session_id: str, *, at: datetime) -> None:
        """
        Set ``revoked_at`` on the session and on each session whose parent it is.

        A record that is already revoked keeps its original ``revoked_at``.
        """
        with self._lock:
            for key, record in self._sessions.items():
                if record.revoked_at is None and session_id in (key, record.parent_session_id):
                    self._sessions[key] = replace(record, revoked_at=at)
