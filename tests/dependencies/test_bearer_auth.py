"""Bearer-token authentication through HTTPBearer, with the per-request auth-session check."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import jwt
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as OrmSession

from kwik.applications import Kwik
from kwik.auth import InMemoryAuthSessionStore, open_session, revoke_session
from kwik.core.enum import Permissions
from kwik.dependencies import current_token  # noqa: TC001 - FastAPI resolves endpoint annotations at runtime
from kwik.dependencies.permissions import has_permission
from kwik.dependencies.session import _get_session
from kwik.dependencies.token import _get_auth_session_store
from kwik.exceptions.auth import InvalidBearerTokenError
from kwik.models.api_key import ApiKey
from kwik.routers import ApiKeyRouter, AuthenticatedRouter
from kwik.security import ALGORITHM, authenticate_from_token, create_token, decode_token

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine

    from kwik.models import User
    from kwik.settings import BaseKwikSettings

PROBE_PATH = "/probe"
ADMIN_PATH = "/admin-only"
KEYED_PATH = "/keyed"
CHALLENGE = "Bearer"
INVALID_TOKEN_CHALLENGE = 'Bearer error="invalid_token"'
EXPIRED_AGO = timedelta(minutes=1)
GHOST_SESSION_ID = "ghost"


def _router() -> APIRouter:
    """Build a router with a bearer-only route, a has_permission route and an API-key route."""
    router = APIRouter()

    probe = AuthenticatedRouter(prefix=PROBE_PATH)

    @probe.get("")
    def probe_route(token: current_token) -> dict[str, int | None]:
        return {"sub": token.sub}

    @router.get(ADMIN_PATH, dependencies=[has_permission(Permissions.impersonification)])
    def admin_route() -> dict[str, bool]:
        return {"ok": True}

    keyed = ApiKeyRouter(prefix=KEYED_PATH)

    @keyed.get("", dependencies=[has_permission(Permissions.impersonification)])
    def keyed_route() -> dict[str, bool]:
        return {"ok": True}

    router.include_router(probe)
    router.include_router(keyed)
    return router


def _bearer(token: str) -> dict[str, str]:
    """Return an Authorization header carrying ``token``."""
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_session(engine: Engine) -> Generator[OrmSession, None, None]:
    """Yield a session joined to an outer transaction rolled back at teardown."""
    connection = engine.connect()
    transaction = connection.begin()
    session = OrmSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _client(kwik: Kwik, session: OrmSession) -> TestClient:
    """Return a test client whose requests use ``session``."""

    def _get_session_override() -> Generator[OrmSession, None, None]:
        yield session

    kwik.app.dependency_overrides[_get_session] = _get_session_override
    return TestClient(kwik.app)


@pytest.fixture
def store() -> InMemoryAuthSessionStore:
    """Return an empty in-memory session store."""
    return InMemoryAuthSessionStore()


@pytest.fixture
def legacy_client(settings: BaseKwikSettings, api_session: OrmSession) -> Generator[TestClient, None, None]:
    """Client for an application without a session store (kwik 1.13 behaviour)."""
    with _client(Kwik(settings=settings, api_router=_router()), api_session) as client:
        yield client


@pytest.fixture
def session_client(
    settings: BaseKwikSettings, api_session: OrmSession, store: InMemoryAuthSessionStore
) -> Generator[TestClient, None, None]:
    """Client for an application configured with an in-memory session store."""
    kwik = Kwik(settings=settings, api_router=_router(), auth_session_store=store)
    with _client(kwik, api_session) as client:
        yield client


def test_missing_header_is_401_with_challenge(legacy_client: TestClient, settings: BaseKwikSettings) -> None:
    """A request without an Authorization header gets 401 and the bare Bearer challenge."""
    response = legacy_client.get(f"{settings.API_V1_STR}{PROBE_PATH}")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == CHALLENGE


def test_non_bearer_scheme_is_401(legacy_client: TestClient, settings: BaseKwikSettings) -> None:
    """A non-Bearer Authorization scheme counts as a missing token."""
    response = legacy_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers={"Authorization": "Basic xxx"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == CHALLENGE


def test_expired_token_is_401_invalid_token(
    legacy_client: TestClient, settings: BaseKwikSettings, admin_user: User
) -> None:
    """An expired token gets 401 with the invalid_token challenge."""
    expired = jwt.encode(
        {"exp": datetime.now(UTC) - EXPIRED_AGO, "sub": str(admin_user.id), "kwik_impersonate": ""},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = legacy_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers=_bearer(expired))
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == INVALID_TOKEN_CHALLENGE


def test_bearer_rejects_refresh_token(
    session_client: TestClient, settings: BaseKwikSettings, store: InMemoryAuthSessionStore, admin_user: User
) -> None:
    """A refresh token is not accepted as a bearer token."""
    token = open_session(user_id=admin_user.id, settings=settings, store=store)
    assert token.refresh_token is not None
    response = session_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers=_bearer(token.refresh_token))
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == INVALID_TOKEN_CHALLENGE


def test_legacy_token_accepted_without_store(
    legacy_client: TestClient, settings: BaseKwikSettings, admin_user: User
) -> None:
    """Without a store, a token without a session id authenticates as in kwik 1.13."""
    token = create_token(user_id=admin_user.id, settings=settings)
    response = legacy_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers=_bearer(token.access_token))
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"sub": admin_user.id}


def test_no_store_ignores_sid(legacy_client: TestClient, settings: BaseKwikSettings, admin_user: User) -> None:
    """Without a store, the session id claim is not checked."""
    token = create_token(user_id=admin_user.id, session_id=GHOST_SESSION_ID, settings=settings)
    response = legacy_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers=_bearer(token.access_token))
    assert response.status_code == HTTPStatus.OK


def test_store_rejects_token_without_sid(
    session_client: TestClient, settings: BaseKwikSettings, admin_user: User
) -> None:
    """With a store, a token without a session id is refused."""
    token = create_token(user_id=admin_user.id, settings=settings)
    response = session_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers=_bearer(token.access_token))
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == INVALID_TOKEN_CHALLENGE


def test_store_accepts_open_session(
    session_client: TestClient, settings: BaseKwikSettings, store: InMemoryAuthSessionStore, admin_user: User
) -> None:
    """With a store, an access token of an open session authenticates."""
    token = open_session(user_id=admin_user.id, settings=settings, store=store)
    response = session_client.get(f"{settings.API_V1_STR}{PROBE_PATH}", headers=_bearer(token.access_token))
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"sub": admin_user.id}


def test_revoked_session_is_401_on_next_request(
    session_client: TestClient, store: InMemoryAuthSessionStore, settings: BaseKwikSettings, admin_user: User
) -> None:
    """Revoking a session refuses its access token on the very next request."""
    url = f"{settings.API_V1_STR}{PROBE_PATH}"
    token = open_session(user_id=admin_user.id, settings=settings, store=store)
    assert session_client.get(url, headers=_bearer(token.access_token)).status_code == HTTPStatus.OK
    session_id = decode_token(token=token.access_token, settings=settings).sid
    assert session_id is not None
    revoke_session(session_id=session_id, store=store)
    assert session_client.get(url, headers=_bearer(token.access_token)).status_code == HTTPStatus.UNAUTHORIZED


def test_has_permission_path_checks_session(
    session_client: TestClient, store: InMemoryAuthSessionStore, settings: BaseKwikSettings, admin_user: User
) -> None:
    """A has_permission route refuses a revoked session with 401, not 403."""
    url = f"{settings.API_V1_STR}{ADMIN_PATH}"
    token = open_session(user_id=admin_user.id, settings=settings, store=store)
    assert session_client.get(url, headers=_bearer(token.access_token)).status_code == HTTPStatus.OK
    session_id = decode_token(token=token.access_token, settings=settings).sid
    assert session_id is not None
    revoke_session(session_id=session_id, store=store)
    response = session_client.get(url, headers=_bearer(token.access_token))
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == INVALID_TOKEN_CHALLENGE


def test_has_permission_path_missing_token_is_401(session_client: TestClient, settings: BaseKwikSettings) -> None:
    """A has_permission route without any credential gets 401 and the Bearer challenge."""
    response = session_client.get(f"{settings.API_V1_STR}{ADMIN_PATH}")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["WWW-Authenticate"] == CHALLENGE


def test_api_key_path_unchanged(
    session_client: TestClient, settings: BaseKwikSettings, api_session: OrmSession, admin_user: User
) -> None:
    """An API key authenticates a has_permission route with a store configured and no bearer token."""
    plaintext = "tbk_" + secrets.token_urlsafe(48)
    api_session.add(
        ApiKey(
            user_id=admin_user.id,
            name="Bearer test key",
            prefix="tbk_",
            key_hash=hashlib.sha256(plaintext.encode()).hexdigest(),
            key_suffix=plaintext[-4:],
        )
    )
    api_session.flush()
    response = session_client.get(f"{settings.API_V1_STR}{KEYED_PATH}", headers={"X-API-Key": plaintext})
    assert response.status_code == HTTPStatus.OK


def test_openapi_declares_http_bearer_only(settings: BaseKwikSettings) -> None:
    """The OpenAPI document declares one HTTP bearer scheme and no OAuth2 password flow."""
    schemes = Kwik(settings=settings, api_router=_router()).app.openapi()["components"]["securitySchemes"]
    assert schemes == {"bearer": {"type": "http", "scheme": "bearer"}}


def test_store_override_is_honoured(
    settings: BaseKwikSettings, api_session: OrmSession, store: InMemoryAuthSessionStore, admin_user: User
) -> None:
    """An application can supply its store by overriding the store dependency."""
    kwik = Kwik(settings=settings, api_router=_router())
    kwik.app.dependency_overrides[_get_auth_session_store] = lambda: store
    url = f"{settings.API_V1_STR}{PROBE_PATH}"
    without_sid = create_token(user_id=admin_user.id, settings=settings)
    with_session = open_session(user_id=admin_user.id, settings=settings, store=store)
    with _client(kwik, api_session) as client:
        assert client.get(url, headers=_bearer(without_sid.access_token)).status_code == HTTPStatus.UNAUTHORIZED
        assert client.get(url, headers=_bearer(with_session.access_token)).status_code == HTTPStatus.OK


def test_authenticate_from_token_checks_store(
    settings: BaseKwikSettings, session: OrmSession, store: InMemoryAuthSessionStore, admin_user: User
) -> None:
    """authenticate_from_token refuses a dead session and returns the user of a live one."""
    live = open_session(user_id=admin_user.id, settings=settings, store=store)
    dead = open_session(user_id=admin_user.id, settings=settings, store=store)
    dead_session_id = decode_token(token=dead.access_token, settings=settings).sid
    assert dead_session_id is not None
    revoke_session(session_id=dead_session_id, store=store)

    with pytest.raises(InvalidBearerTokenError):
        authenticate_from_token(token=dead.access_token, settings=settings, session=session, store=store)
    user = authenticate_from_token(token=live.access_token, settings=settings, session=session, store=store)
    assert user.id == admin_user.id
