"""
Prove a revocation written through the request's database session survives the 401 of ``/login/refresh``.

These tests build their own ``Kwik`` app with real request sessions, as
``tests/dependencies/test_commit_before_response.py`` does: the ``client`` fixture binds the app to a
rolled-back connection, where kwik's commit only releases a SAVEPOINT and nothing is visible elsewhere.
The store records each write as a ``Role`` row whose name starts with ``MARKER_PREFIX``; every test
deletes those rows at the end.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from kwik.api.api import api_router
from kwik.applications import Kwik
from kwik.auth import InMemoryAuthSessionStore, open_session, revoke_session
from kwik.database import create_session
from kwik.dependencies import Session  # noqa: TC001 - FastAPI resolves the override's annotation at runtime
from kwik.dependencies.token import _get_auth_session_store
from kwik.models import Base, Role
from kwik.security import decode_token

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session as OrmSession

    from kwik.auth import AuthSession
    from kwik.models import User
    from kwik.schemas import Token
    from kwik.settings import BaseKwikSettings

REFRESH_URL = "/api/v1/login/refresh"
NO_GRACE_SECONDS = 0
MARKER_PREFIX = "auth-store-write:"
REVOKE_MARKER = f"{MARKER_PREFIX}revoke:"
GET_MARKER = f"{MARKER_PREFIX}get:"
REUSE_DETAIL = "Refresh token reused; session revoked"
INVALID_TOKEN_CHALLENGE = 'Bearer error="invalid_token"'


class RequestBoundStore:
    """
    An auth session store that writes through the request's database session, as a SQL store would.

    Records live in an in-memory store shared across requests. ``revoke`` also adds and flushes a
    marker row through the request session, standing in for the store's ``UPDATE``; ``get`` does the
    same only when ``write_on_get`` is set. ``create``, ``update`` and ``rotate`` write nothing to the
    database, so the markers are the only rows this store can leave behind.
    """

    def __init__(
        self, inner: InMemoryAuthSessionStore, db: OrmSession, creator_user_id: int, *, write_on_get: bool
    ) -> None:
        """Wrap ``inner`` and write markers through ``db``, the request's session."""
        self.inner = inner
        self.db = db
        self.creator_user_id = creator_user_id
        self.write_on_get = write_on_get

    def _mark(self, name: str) -> None:
        """Write a marker row through the request session and flush it, without committing."""
        self.db.add(Role(name=name, is_active=True, creator_user_id=self.creator_user_id))
        self.db.flush()

    def create(self, session: AuthSession) -> None:
        """Delegate to the inner store."""
        self.inner.create(session)

    def get(self, session_id: str) -> AuthSession | None:
        """Delegate to the inner store, writing a marker first when ``write_on_get`` is set."""
        if self.write_on_get:
            self._mark(f"{GET_MARKER}{session_id}")
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
        """Delegate to the inner store."""
        return self.inner.rotate(
            session_id,
            expected_token_id=expected_token_id,
            new_token_id=new_token_id,
            expires_at=expires_at,
            rotated_at=rotated_at,
        )

    def revoke(self, session_id: str, *, at: datetime) -> None:
        """Write the revocation marker through the request session, then delegate."""
        self._mark(f"{REVOKE_MARKER}{session_id}")
        self.inner.revoke(session_id, at=at)


def _store_override(
    inner: InMemoryAuthSessionStore, creator_user_id: int, *, write_on_get: bool
) -> Callable[[OrmSession], RequestBoundStore]:
    """Build the ``_get_auth_session_store`` override that binds the store to the request session."""

    def request_bound_store(session: Session) -> RequestBoundStore:
        """Return the store bound to this request's database session."""
        return RequestBoundStore(inner, session, creator_user_id, write_on_get=write_on_get)

    return request_bound_store


def _sid(token: Token, settings: BaseKwikSettings) -> str:
    """Return the session id carried by the access token of ``token``."""
    sid = decode_token(token=token.access_token, settings=settings).sid
    assert sid is not None
    return sid


def _committed_markers(engine: Engine) -> set[str]:
    """Return the marker names visible from a connection of its own, so only committed rows count."""
    with create_session(engine=engine) as other:
        return set(other.scalars(select(Role.name).where(Role.name.startswith(MARKER_PREFIX))))


def _committed_row_counts(engine: Engine) -> dict[str, int]:
    """Count the committed rows of every kwik table from a connection of its own."""
    with create_session(engine=engine) as other:
        return {
            table.name: other.scalar(select(func.count()).select_from(table)) or 0
            for table in Base.metadata.sorted_tables
        }


def _delete_markers(engine: Engine) -> None:
    """Remove the marker rows a test committed for real."""
    with create_session(engine=engine) as cleanup:
        cleanup.execute(delete(Role).where(Role.name.startswith(MARKER_PREFIX)))
        cleanup.commit()


def _client(
    settings: BaseKwikSettings, inner: InMemoryAuthSessionStore, admin_user: User, *, write_on_get: bool
) -> TestClient:
    """Build a client for a Kwik app with real request sessions and the request-bound store."""
    kwik = Kwik(settings=settings, api_router=api_router)
    kwik.app.dependency_overrides[_get_auth_session_store] = _store_override(
        inner, admin_user.id, write_on_get=write_on_get
    )
    return TestClient(kwik.app)


@pytest.fixture
def clean_markers(engine: Engine) -> Iterator[None]:
    """Delete any committed marker rows after the test."""
    yield
    _delete_markers(engine)


@pytest.mark.usefixtures("clean_markers")
def test_reuse_commits_revocation_and_nothing_else(
    settings: BaseKwikSettings, engine: Engine, admin_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Refresh-token reuse answers 401 and the store's revocation, written through the request session, is committed.

    Row counts of every kwik table, read from another connection before and after the reuse request,
    differ by the one revocation marker: the request committed nothing else.
    """
    inner = InMemoryAuthSessionStore()
    first = open_session(user_id=admin_user.id, settings=settings, store=inner)
    sid = _sid(first, settings)
    with _client(settings, inner, admin_user, write_on_get=False) as client:
        rotated = client.post(REFRESH_URL, json={"refresh_token": first.refresh_token})
        assert rotated.status_code == HTTPStatus.OK
        before = _committed_row_counts(engine)
        monkeypatch.setattr(settings, "REFRESH_REUSE_GRACE_SECONDS", NO_GRACE_SECONDS)
        reused = client.post(REFRESH_URL, json={"refresh_token": first.refresh_token})
    assert reused.status_code == HTTPStatus.UNAUTHORIZED
    assert reused.headers["WWW-Authenticate"] == INVALID_TOKEN_CHALLENGE
    assert reused.json()["detail"] == REUSE_DETAIL
    assert _committed_markers(engine) == {f"{REVOKE_MARKER}{sid}"}
    after = _committed_row_counts(engine)
    assert after == {**before, Role.__tablename__: before[Role.__tablename__] + 1}


@pytest.mark.usefixtures("clean_markers")
def test_plain_refusal_commits_nothing(settings: BaseKwikSettings, engine: Engine, admin_user: User) -> None:
    """A refusal that revokes nothing (InvalidBearerTokenError) rolls back the store's pending write."""
    inner = InMemoryAuthSessionStore()
    token = open_session(user_id=admin_user.id, settings=settings, store=inner)
    revoke_session(session_id=_sid(token, settings), store=inner)
    with _client(settings, inner, admin_user, write_on_get=True) as client:
        refused = client.post(REFRESH_URL, json={"refresh_token": token.refresh_token})
    assert refused.status_code == HTTPStatus.UNAUTHORIZED
    assert refused.headers["WWW-Authenticate"] == INVALID_TOKEN_CHALLENGE
    assert refused.json()["detail"] != REUSE_DETAIL
    assert _committed_markers(engine) == set()
