"""Tests for the AuthSession record and the in-memory session store."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from kwik.auth import AuthSession, InMemoryAuthSessionStore

NOW = datetime(2026, 1, 1, tzinfo=UTC)
EXPIRES = NOW + timedelta(days=30)
LATER = NOW + timedelta(hours=1)
ONE_SECOND = timedelta(seconds=1)
USER_ID = 7
ADMIN_ID = 1


def _session(session_id: str = "s-1", **overrides: object) -> AuthSession:
    """Build a session record with fixed timestamps; keyword arguments override fields."""
    fields: dict[str, object] = {
        "id": session_id,
        "user_id": USER_ID,
        "created_at": NOW,
        "expires_at": EXPIRES,
        "refresh_token_id": "jti-1",
    }
    fields.update(overrides)
    return AuthSession(**fields)  # type: ignore[arg-type]


def test_create_then_get_returns_equal_record() -> None:
    """A created record is returned by get with the same field values."""
    store = InMemoryAuthSessionStore()
    record = _session()
    store.create(record)
    assert store.get(record.id) == record


def test_get_unknown_returns_none() -> None:
    """Get returns None for an id the store has never seen."""
    assert InMemoryAuthSessionStore().get("missing") is None


def test_update_replaces_record() -> None:
    """Update stores the new field values under the same id."""
    store = InMemoryAuthSessionStore()
    store.create(_session())
    updated = _session(expires_at=LATER)
    store.update(updated)
    assert store.get(updated.id) == updated


def test_revoke_sets_revoked_at_and_cascades_to_children() -> None:
    """Revoke marks the session and every session whose parent it is, and leaves others alone."""
    store = InMemoryAuthSessionStore()
    store.create(_session("parent", user_id=ADMIN_ID))
    store.create(_session("child", impersonator_user_id=ADMIN_ID, parent_session_id="parent"))
    store.create(_session("unrelated"))

    store.revoke("parent", at=LATER)

    assert store.get("parent").revoked_at == LATER
    assert store.get("child").revoked_at == LATER
    assert store.get("unrelated").revoked_at is None


def test_rotate_matches_expected_id_and_returns_new_record() -> None:
    """Rotate with the current token id moves it to previous and installs the new id and expiry."""
    store = InMemoryAuthSessionStore()
    store.create(_session())
    new_expires = EXPIRES + timedelta(hours=1)

    rotated = store.rotate(
        "s-1", expected_token_id="jti-1", new_token_id="jti-2", expires_at=new_expires, rotated_at=LATER
    )

    assert rotated is not None
    assert (rotated.refresh_token_id, rotated.previous_refresh_token_id) == ("jti-2", "jti-1")
    assert (rotated.expires_at, rotated.rotated_at) == (new_expires, LATER)
    assert store.get("s-1") == rotated


def test_rotate_with_stale_expected_id_returns_none_and_changes_nothing() -> None:
    """Rotate with a token id that is no longer current loses the compare-and-set."""
    store = InMemoryAuthSessionStore()
    original = _session(refresh_token_id="jti-2", previous_refresh_token_id="jti-1", rotated_at=NOW)
    store.create(original)

    result = store.rotate("s-1", expected_token_id="jti-1", new_token_id="jti-3", expires_at=LATER, rotated_at=LATER)

    assert result is None
    assert store.get("s-1") == original
    assert (
        store.rotate("missing", expected_token_id="jti-1", new_token_id="x", expires_at=LATER, rotated_at=LATER) is None
    )


def test_is_active_false_when_revoked_or_expired() -> None:
    """A session is active only while it is unrevoked and its expiry is in the future."""
    record = _session()
    assert record.is_active(now=NOW)
    assert not record.is_active(now=EXPIRES)
    assert not record.is_active(now=EXPIRES + ONE_SECOND)
    assert not replace(record, revoked_at=NOW).is_active(now=NOW)


def test_store_returns_copies() -> None:
    """Mutating a returned record does not change what the store holds."""
    store = InMemoryAuthSessionStore()
    record = _session()
    store.create(record)
    fetched = store.get(record.id)
    assert fetched is not None
    fetched.revoked_at = LATER
    record.revoked_at = LATER
    assert store.get(record.id).revoked_at is None
