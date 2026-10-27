"""
Open, refresh and revoke auth sessions, and check them on authenticated requests.

A session pairs a short-lived access token with a rotating refresh token. Each refresh
installs a new refresh token id through the store's compare-and-set; presenting the previous
refresh token again within ``REFRESH_REUSE_GRACE_SECONDS`` returns the same successor (two
tabs refreshing at once), and any other reuse revokes the whole session.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final

from kwik.exceptions.auth import InvalidBearerTokenError, SessionRevokedError
from kwik.exceptions.base import TokenValidationError
from kwik.security import create_refresh_token, create_token, decode_token

from .store import AuthSession

if TYPE_CHECKING:
    from kwik.schemas import Token, TokenPayload
    from kwik.settings import BaseKwikSettings

    from .store import AuthSessionStore

ID_BYTES: Final[int] = 24


def _new_id() -> str:
    """Return a random URL-safe id for a session or a refresh token."""
    return secrets.token_urlsafe(ID_BYTES)


def _whole_seconds(moment: datetime) -> datetime:
    """
    Drop the microseconds of ``moment``.

    ``expires_at`` becomes the refresh token's ``exp`` claim, which PyJWT encodes in whole
    seconds, so the record stores exactly what the token says and a re-mint is identical.
    """
    return moment.replace(microsecond=0)


def _refresh_expiry(now: datetime, settings: BaseKwikSettings) -> datetime:
    """Return the refresh expiry for a session opened or rotated at ``now``."""
    return _whole_seconds(now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))


def _pair(record: AuthSession, settings: BaseKwikSettings) -> Token:
    """
    Mint the access and refresh tokens for the current generation of ``record``.

    Every claim comes from the record, never from a presented token, so the refresh token is
    the same string each time it is minted for the same generation.
    """
    token = create_token(
        user_id=record.user_id,
        impersonator_user_id=record.impersonator_user_id,
        session_id=record.id,
        settings=settings,
    )
    token.refresh_token = create_refresh_token(
        user_id=record.user_id,
        session_id=record.id,
        token_id=record.refresh_token_id,
        expires_at=record.expires_at,
        settings=settings,
    )
    return token


def open_session(  # noqa: PLR0913
    *,
    user_id: int,
    settings: BaseKwikSettings,
    store: AuthSessionStore,
    impersonator_user_id: int | None = None,
    parent_session_id: str | None = None,
    now: datetime | None = None,
) -> Token:
    """
    Create and persist a session for ``user_id`` and return its access and refresh tokens.

    An impersonation session passes the impersonator and the impersonator's own session, so
    revoking that session also revokes this one.

    Raises:
        ValueError: If ``impersonator_user_id`` is given without ``parent_session_id``.

    """
    if impersonator_user_id is not None and parent_session_id is None:
        msg = "An impersonation session needs the impersonator's parent_session_id"
        raise ValueError(msg)
    now = now or datetime.now(UTC)
    record = AuthSession(
        id=_new_id(),
        user_id=user_id,
        created_at=now,
        expires_at=_refresh_expiry(now, settings),
        refresh_token_id=_new_id(),
        impersonator_user_id=impersonator_user_id,
        parent_session_id=parent_session_id,
    )
    store.create(record)
    return _pair(record, settings)


def refresh_session(
    *,
    refresh_token: str,
    settings: BaseKwikSettings,
    store: AuthSessionStore,
    now: datetime | None = None,
) -> Token:
    """
    Exchange a refresh token for a new access and refresh token pair.

    The current refresh token rotates. The previous one, presented again within
    ``REFRESH_REUSE_GRACE_SECONDS`` of the rotation, returns the same successor. Any other
    token for the session is reuse and revokes the session and its impersonation children.

    Raises:
        SessionRevokedError: After revoking the session, if the token was reused, or if it is an
            impersonation session whose parent session is unknown, revoked or expired. Under a
            ``Kwik`` app the request's database session is committed before it propagates, so a
            revocation the store wrote through that session is kept.
        InvalidBearerTokenError: If the token is invalid, expired or not a refresh token, or if
            the session is unknown, revoked or expired; nothing is revoked.

    """
    now = now or datetime.now(UTC)
    try:
        payload = decode_token(token=refresh_token, settings=settings, token_type="refresh")  # noqa: S106
    except TokenValidationError:
        raise InvalidBearerTokenError from None
    record = store.get(payload.sid) if payload.sid else None
    if record is None or not record.is_active(now=now):
        raise InvalidBearerTokenError
    if record.parent_session_id is not None:
        # An impersonation session cannot outlive the impersonator's session; a dead parent
        # does not come back, so the child is revoked for good.
        parent = store.get(record.parent_session_id)
        if parent is None or not parent.is_active(now=now):
            store.revoke(record.id, at=now)
            raise SessionRevokedError
    if payload.jti == record.refresh_token_id:
        # Current generation: rotate through the store's compare-and-set.
        rotated = store.rotate(
            record.id,
            expected_token_id=payload.jti,
            new_token_id=_new_id(),
            expires_at=_refresh_expiry(now, settings),
            rotated_at=now,
        )
        if rotated is not None:
            return _pair(rotated, settings)
        # Another request rotated first: re-read and fall through to the grace check.
        record = store.get(record.id)
        if record is None or not record.is_active(now=now):
            raise InvalidBearerTokenError
    grace = timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS)
    if (
        payload.jti == record.previous_refresh_token_id
        and record.rotated_at is not None
        and now - record.rotated_at <= grace
    ):
        # Same successor: the claims are re-minted from the record, so the string is identical.
        return _pair(record, settings)
    store.revoke(record.id, at=now)
    raise SessionRevokedError(detail="Refresh token reused; session revoked")


def revoke_session(*, session_id: str, store: AuthSessionStore, now: datetime | None = None) -> None:
    """Revoke the session and every impersonation session opened from it."""
    store.revoke(session_id, at=now or datetime.now(UTC))


def require_active_session(
    *,
    payload: TokenPayload,
    store: AuthSessionStore | None,
    now: datetime | None = None,
) -> AuthSession | None:
    """
    Check that an access token's session is active and return its record.

    Without a store the application runs as kwik 1.13 did and this returns None.

    Raises:
        InvalidBearerTokenError: If the token carries no session id, is not an access token,
            or its session is unknown, revoked or expired.

    """
    if store is None:
        return None
    if payload.sid is None or payload.typ != "access":
        raise InvalidBearerTokenError
    record = store.get(payload.sid)
    if record is None or not record.is_active(now=now or datetime.now(UTC)):
        raise InvalidBearerTokenError
    return record
