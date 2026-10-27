"""The auth session record and the store protocol an application implements to persist it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class AuthSession:
    """
    One signed-in session; the application persists it (kwik adds no table).

    Every datetime is tz-aware UTC. ``expires_at`` is the refresh expiry in whole seconds and
    moves forward on every rotation; ``refresh_token_id`` is the ``jti`` of the current refresh
    token and ``previous_refresh_token_id`` the one it replaced. An impersonation session names
    the impersonator and, in ``parent_session_id``, the impersonator's own session.
    """

    id: str
    user_id: int
    created_at: datetime
    expires_at: datetime
    refresh_token_id: str
    impersonator_user_id: int | None = None
    parent_session_id: str | None = None
    previous_refresh_token_id: str | None = None
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None

    def is_active(self, *, now: datetime) -> bool:
        """Return whether the session is unrevoked and has not reached its expiry at ``now``."""
        return self.revoked_at is None and self.expires_at > now


class AuthSessionStore(Protocol):
    """
    What an application persists for auth sessions.

    Every datetime is tz-aware UTC. ``get`` runs on every authenticated request, so it should
    be a primary-key lookup.
    """

    def create(self, session: AuthSession) -> None:
        """Persist a new session record."""

    def get(self, session_id: str) -> AuthSession | None:
        """Return the session record with ``session_id``, or None when there is none."""

    def update(self, session: AuthSession) -> None:
        """
        Replace the stored record with ``session``.

        For application use (hard caps, revoke-on-deactivation); ``refresh_session`` never calls it.
        """

    def rotate(
        self,
        session_id: str,
        *,
        expected_token_id: str,
        new_token_id: str,
        expires_at: datetime,
        rotated_at: datetime,
    ) -> AuthSession | None:
        """
        Install a new refresh token id as one compare-and-set, returning the updated record.

        Only when the record's ``refresh_token_id`` equals ``expected_token_id``, set
        ``previous_refresh_token_id=expected_token_id``, ``refresh_token_id=new_token_id``,
        ``expires_at`` and ``rotated_at``, and return the new record. Return None when another
        rotation won or the session does not exist. In SQL this is one
        ``UPDATE ... WHERE id = :id AND refresh_token_id = :expected RETURNING *``.
        """

    def revoke(self, session_id: str, *, at: datetime) -> None:
        """Set ``revoked_at`` on the session and on every session whose ``parent_session_id`` is it."""
