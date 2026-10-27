"""Tests for the auth session service: open, refresh with rotation and reuse detection, revoke."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from kwik.auth import (
    AuthSession,
    InMemoryAuthSessionStore,
    open_session,
    refresh_session,
    require_active_session,
    revoke_session,
)
from kwik.exceptions import (
    AuthSessionsNotConfiguredError,
    InvalidBearerTokenError,
    MissingBearerTokenError,
    kwik_exception_handler,
)
from kwik.schemas import TokenPayload
from kwik.security import SECONDS_PER_MINUTE, decode_token

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.schemas import Token
    from kwik.settings import BaseKwikSettings

USER_ID = 7
ADMIN_ID = 1
ONE_SECOND = timedelta(seconds=1)
ONE_HOUR = timedelta(hours=1)
ROTATIONS = 3


def _grace(settings: BaseKwikSettings) -> timedelta:
    """Return the refresh reuse grace window configured in ``settings``."""
    return timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS)


def _sid(token: Token, settings: BaseKwikSettings) -> str:
    """Return the session id carried by the access token of ``token``."""
    sid = decode_token(token=token.access_token, settings=settings).sid
    assert sid is not None
    return sid


def _record(store: InMemoryAuthSessionStore, sid: str) -> AuthSession:
    """Return the stored record for ``sid``, failing the test when it is missing."""
    record = store.get(sid)
    assert record is not None
    return record


class RacingStore(InMemoryAuthSessionStore):
    """
    A store whose first rotate loses, as if a concurrent request had rotated first.

    It delegates every call to an inner in-memory store. On the first :meth:`rotate` it runs
    ``other_request`` (the concurrent tab, refreshing through the inner store) and returns None
    without writing, as a compare-and-set that lost the race would.
    """

    def __init__(self, inner: InMemoryAuthSessionStore, other_request: Callable[[], None]) -> None:
        """Wrap ``inner``; ``other_request`` runs once, inside the first rotate."""
        self.inner = inner
        self.other_request = other_request
        self.lost_once = False

    def create(self, session: AuthSession) -> None:
        """Delegate to the inner store."""
        self.inner.create(session)

    def get(self, session_id: str) -> AuthSession | None:
        """Delegate to the inner store."""
        return self.inner.get(session_id)

    def update(self, session: AuthSession) -> None:
        """Delegate to the inner store."""
        self.inner.update(session)

    def rotate(
        self,
        session_id: str,
        *,
        expected_token_id: str,
        new_token_id: str,
        expires_at: datetime,
        rotated_at: datetime,
    ) -> AuthSession | None:
        """Lose the first compare-and-set to ``other_request``; delegate afterwards."""
        if not self.lost_once:
            self.lost_once = True
            self.other_request()
            return None
        return self.inner.rotate(
            session_id,
            expected_token_id=expected_token_id,
            new_token_id=new_token_id,
            expires_at=expires_at,
            rotated_at=rotated_at,
        )

    def revoke(self, session_id: str, *, at: datetime) -> None:
        """Delegate to the inner store."""
        self.inner.revoke(session_id, at=at)


def test_open_session_persists_record_and_returns_pair(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """Opening a session stores its record and returns matching access and refresh tokens."""
    token = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    access = decode_token(token=token.access_token, settings=settings)
    refresh = decode_token(token=token.refresh_token, settings=settings, token_type="refresh")
    record = _record(store, access.sid)
    assert (record.user_id, record.refresh_token_id, record.created_at) == (USER_ID, refresh.jti, now)
    assert record.expires_at == now + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    assert (record.impersonator_user_id, record.parent_session_id, record.revoked_at) == (None, None, None)
    assert (access.sub, access.typ, access.kwik_impersonate) == (USER_ID, "access", "")
    assert (refresh.sub, refresh.sid) == (USER_ID, access.sid)
    assert token.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * SECONDS_PER_MINUTE


def test_open_session_issues_distinct_ids(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """Two sessions for the same user get different session and refresh token ids."""
    first = open_session(user_id=USER_ID, settings=settings, store=store)
    second = open_session(user_id=USER_ID, settings=settings, store=store)
    assert _sid(first, settings) != _sid(second, settings)
    assert first.refresh_token != second.refresh_token


def test_open_impersonation_session_records_both_users(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """An impersonation session records the impersonator and the parent session."""
    parent = open_session(user_id=ADMIN_ID, settings=settings, store=store, now=now)
    parent_sid = _sid(parent, settings)
    child = open_session(
        user_id=USER_ID,
        impersonator_user_id=ADMIN_ID,
        parent_session_id=parent_sid,
        settings=settings,
        store=store,
        now=now,
    )
    payload = decode_token(token=child.access_token, settings=settings)
    assert (payload.sub, payload.kwik_impersonate) == (USER_ID, str(ADMIN_ID))
    record = _record(store, payload.sid)
    assert (record.impersonator_user_id, record.parent_session_id) == (ADMIN_ID, parent_sid)


def test_open_impersonation_requires_parent(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """An impersonator without a parent session is a programming error."""
    with pytest.raises(ValueError, match="parent_session_id"):
        open_session(user_id=USER_ID, impersonator_user_id=ADMIN_ID, settings=settings, store=store)


def test_refresh_rotates_and_extends(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """Refreshing installs a new refresh token id, remembers the old one and moves the expiry."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    later = now + ONE_HOUR
    second = refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=later)
    old = decode_token(token=first.refresh_token, settings=settings, token_type="refresh")
    new = decode_token(token=second.refresh_token, settings=settings, token_type="refresh")
    record = _record(store, old.sid)
    assert new.sid == old.sid
    assert new.jti != old.jti
    assert (record.refresh_token_id, record.previous_refresh_token_id, record.rotated_at) == (new.jti, old.jti, later)
    assert record.expires_at == later + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    assert _sid(second, settings) == old.sid
    assert second.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * SECONDS_PER_MINUTE


def test_refresh_stores_whole_second_expiry(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """The stored expiry has no microseconds, so it equals the refresh token's exp claim."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=datetime.now(UTC).replace(microsecond=1))
    refresh_session(refresh_token=first.refresh_token, settings=settings, store=store)
    record = _record(store, _sid(first, settings))
    assert record.expires_at.microsecond == 0


def test_refresh_keeps_impersonation_claim(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """A refreshed impersonation session still names the impersonator in the access token."""
    parent = open_session(user_id=ADMIN_ID, settings=settings, store=store, now=now)
    child = open_session(
        user_id=USER_ID,
        impersonator_user_id=ADMIN_ID,
        parent_session_id=_sid(parent, settings),
        settings=settings,
        store=store,
        now=now,
    )
    refreshed = refresh_session(refresh_token=child.refresh_token, settings=settings, store=store, now=now + ONE_SECOND)
    payload = decode_token(token=refreshed.access_token, settings=settings)
    assert (payload.sub, payload.kwik_impersonate) == (USER_ID, str(ADMIN_ID))


def test_refresh_within_grace_returns_identical_successor(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """The previous refresh token presented inside the grace window yields the same successor."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    second = refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=now + ONE_SECOND)
    again = refresh_session(
        refresh_token=first.refresh_token,
        settings=settings,
        store=store,
        now=now + ONE_SECOND + _grace(settings),
    )
    sid = _sid(second, settings)
    assert again.refresh_token == second.refresh_token
    assert _sid(again, settings) == sid
    assert _record(store, sid).revoked_at is None


def test_refresh_previous_after_grace_revokes_session(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """The previous refresh token presented after the grace window revokes the whole session."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    second = refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=now + ONE_SECOND)
    sid = _sid(second, settings)
    late = now + ONE_SECOND + _grace(settings) + ONE_SECOND
    with pytest.raises(InvalidBearerTokenError) as reused:
        refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=late)
    assert reused.value.detail == "Refresh token reused; session revoked"
    assert _record(store, sid).revoked_at == late
    with pytest.raises(InvalidBearerTokenError):  # the successor is dead too
        refresh_session(refresh_token=second.refresh_token, settings=settings, store=store, now=late + ONE_SECOND)


def test_refresh_unknown_generation_revokes_session(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """A refresh token older than the previous generation is reuse, even inside the grace window."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    current = first
    for _ in range(ROTATIONS):
        current = refresh_session(refresh_token=current.refresh_token, settings=settings, store=store, now=now)
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=now)
    assert _record(store, _sid(first, settings)).revoked_at == now
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=current.refresh_token, settings=settings, store=store, now=now)


def test_refresh_revoked_session_refused(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """A revoked session cannot be refreshed, and the refusal changes nothing."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    sid = _sid(first, settings)
    revoke_session(session_id=sid, store=store, now=now)
    before = _record(store, sid)
    assert before.revoked_at == now
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=now + ONE_SECOND)
    assert _record(store, sid) == before


def test_revoke_session_defaults_to_wall_clock(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """Without an injected clock, revoke_session stamps the current UTC time."""
    sid = _sid(open_session(user_id=USER_ID, settings=settings, store=store), settings)
    before = datetime.now(UTC)
    revoke_session(session_id=sid, store=store)
    revoked_at = _record(store, sid).revoked_at
    assert revoked_at is not None
    assert revoked_at >= before


def test_refresh_refused_when_store_expired_session(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """A store that shortens expires_at (a hard cap) is obeyed even while the token's exp is ahead."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    sid = _sid(first, settings)
    store.update(replace(_record(store, sid), expires_at=now - ONE_SECOND))
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=now)


def test_refresh_unknown_session_refused(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """A valid refresh token whose session the store does not know is refused."""
    token = open_session(user_id=USER_ID, settings=settings, store=InMemoryAuthSessionStore())
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=token.refresh_token, settings=settings, store=store)


def test_lost_rotation_race_takes_grace_path(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """A refresh that loses the compare-and-set re-reads the record and returns the winner's successor."""
    winners: list[Token] = []
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)

    def other_tab() -> None:
        """Refresh the same token through the inner store, winning the race."""
        winners.append(refresh_session(refresh_token=first.refresh_token, settings=settings, store=store, now=now))

    racing_store = RacingStore(store, other_tab)
    loser = refresh_session(
        refresh_token=first.refresh_token, settings=settings, store=racing_store, now=now + ONE_SECOND
    )
    assert racing_store.lost_once
    [winner] = winners
    assert loser.refresh_token == winner.refresh_token
    assert _record(store, _sid(first, settings)).revoked_at is None


def test_lost_rotation_race_on_revoked_session_refused(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """When the concurrent request revoked the session, the re-read refuses the loser."""
    first = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    sid = _sid(first, settings)
    racing_store = RacingStore(store, lambda: revoke_session(session_id=sid, store=store, now=now))
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=first.refresh_token, settings=settings, store=racing_store, now=now)
    assert racing_store.lost_once


def test_refresh_rejects_access_token(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """An access token is not a refresh token."""
    token = open_session(user_id=USER_ID, settings=settings, store=store)
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token=token.access_token, settings=settings, store=store)


def test_refresh_rejects_garbage(settings: BaseKwikSettings, store: InMemoryAuthSessionStore) -> None:
    """A string that is not a JWT is refused with the 401 error, not the decoder's 400."""
    with pytest.raises(InvalidBearerTokenError):
        refresh_session(refresh_token="not-a-token", settings=settings, store=store)


def test_require_active_session_without_store_returns_none(settings: BaseKwikSettings) -> None:
    """Without a store kwik behaves as 1.13: no session check."""
    store = InMemoryAuthSessionStore()
    token = open_session(user_id=USER_ID, settings=settings, store=store)
    with_sid = decode_token(token=token.access_token, settings=settings)
    without_sid = TokenPayload(sub=USER_ID, kwik_impersonate="")
    assert require_active_session(payload=with_sid, store=None) is None
    assert require_active_session(payload=without_sid, store=None) is None


def test_require_active_session_rejects_missing_sid(store: InMemoryAuthSessionStore) -> None:
    """With a store configured, a token without a session id is refused."""
    with pytest.raises(InvalidBearerTokenError):
        require_active_session(payload=TokenPayload(sub=USER_ID, kwik_impersonate=""), store=store)


def test_require_active_session_rejects_refresh_payload(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore
) -> None:
    """A refresh token payload does not authenticate a request."""
    token = open_session(user_id=USER_ID, settings=settings, store=store)
    payload = decode_token(token=token.refresh_token, settings=settings, token_type="refresh")
    with pytest.raises(InvalidBearerTokenError):
        require_active_session(payload=payload, store=store)


def test_require_active_session_rejects_unknown_revoked_expired(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """Unknown, revoked and expired sessions are all refused."""
    unknown = TokenPayload(sub=USER_ID, kwik_impersonate="", sid="missing", typ="access")
    with pytest.raises(InvalidBearerTokenError):
        require_active_session(payload=unknown, store=store, now=now)

    revoked = decode_token(
        token=open_session(user_id=USER_ID, settings=settings, store=store).access_token, settings=settings
    )
    revoke_session(session_id=revoked.sid, store=store, now=now)
    with pytest.raises(InvalidBearerTokenError):
        require_active_session(payload=revoked, store=store, now=now)

    expired = decode_token(
        token=open_session(user_id=USER_ID, settings=settings, store=store).access_token, settings=settings
    )
    expires_at = _record(store, expired.sid).expires_at
    with pytest.raises(InvalidBearerTokenError):
        require_active_session(payload=expired, store=store, now=expires_at)


def test_require_active_session_returns_record(
    settings: BaseKwikSettings, store: InMemoryAuthSessionStore, now: datetime
) -> None:
    """An active session's record is returned."""
    token = open_session(user_id=USER_ID, settings=settings, store=store, now=now)
    payload = decode_token(token=token.access_token, settings=settings)
    assert require_active_session(payload=payload, store=store, now=now) == _record(store, payload.sid)
    assert require_active_session(payload=payload, store=store) == _record(store, payload.sid)


def test_exceptions_carry_www_authenticate() -> None:
    """The 401 errors carry the RFC 6750 challenge; the unconfigured-store error is a 501."""
    invalid = InvalidBearerTokenError()
    missing = MissingBearerTokenError()
    not_configured = AuthSessionsNotConfiguredError()
    assert (invalid.status_code, invalid.detail) == (HTTPStatus.UNAUTHORIZED, "Invalid or expired token")
    assert invalid.headers == {"WWW-Authenticate": 'Bearer error="invalid_token"'}
    assert (missing.status_code, missing.detail) == (HTTPStatus.UNAUTHORIZED, "Not authenticated")
    assert missing.headers == {"WWW-Authenticate": "Bearer"}
    assert (not_configured.status_code, not_configured.detail) == (
        HTTPStatus.NOT_IMPLEMENTED,
        "Auth sessions are not configured",
    )
    assert not_configured.headers is None


async def test_http_exc_and_handler_pass_headers() -> None:
    """KwikError headers reach both the HTTPException and the JSON response."""
    error = InvalidBearerTokenError()
    assert error.http_exc.headers == error.headers
    response = await kwik_exception_handler(None, error)  # type: ignore[arg-type]
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'
