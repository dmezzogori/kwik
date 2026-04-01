"""Tests for the verify_api_key FastAPI dependency."""

# NOTE: Do NOT use `from __future__ import annotations` here.
# FastAPI needs to evaluate type annotations at runtime to resolve
# dependencies like ApiKeyContext. PEP 563 deferred evaluation breaks this.

import hashlib
import secrets
from collections.abc import Generator
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SASession

from kwik.database import create_session
from kwik.dependencies.api_key import ApiKeyContext
from kwik.dependencies.permissions import has_permission
from kwik.dependencies.session import _get_session
from kwik.exceptions import KwikError, kwik_exception_handler
from kwik.models.api_key import ApiKey
from kwik.models.user import Permission, Role, RolePermission, User, UserRole
from kwik.routers import ApiKeyRouter
from kwik.security import get_password_hash
from kwik.settings import BaseKwikSettings


def _make_key() -> tuple[str, str]:
    """Generate a plaintext key and its SHA-256 hash."""
    raw = "tbk_" + secrets.token_urlsafe(48)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


def _create_user(session: SASession, *, is_active: bool = True, email: str = "test@example.com") -> User:
    """Create a test user."""
    user = User(
        name="Test",
        surname="User",
        email=email,
        hashed_password=get_password_hash("password"),
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def _create_api_key(  # noqa: PLR0913
    session: SASession,
    user: User,
    plaintext: str,
    key_hash: str,
    *,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> ApiKey:
    """Create an API key row."""
    api_key = ApiKey(
        user_id=user.id,
        name="Test Key",
        prefix="tbk_",
        key_hash=key_hash,
        key_suffix=plaintext[-4:],
        expires_at=expires_at,
        revoked_at=revoked_at,
    )
    session.add(api_key)
    session.flush()
    return api_key


@pytest.fixture
def app_and_client(engine: object) -> Generator[tuple[FastAPI, TestClient, SASession], None, None]:
    """
    Create a FastAPI app with an ApiKeyRouter endpoint and a test client.

    Provides an app, client, and session for testing API key authentication.
    """
    app = FastAPI()
    app.state.settings = BaseKwikSettings()
    app.exception_handler(KwikError)(kwik_exception_handler)

    router = ApiKeyRouter(prefix="/test")

    @router.get("/protected")
    def protected_endpoint(context: ApiKeyContext) -> dict:
        return {"user_id": context.user.id}

    @router.get(
        "/with-permission",
        dependencies=(has_permission("monitoring_read"),),
    )
    def permission_endpoint(context: ApiKeyContext) -> dict:
        return {"user_id": context.user.id}

    app.include_router(router)

    session = create_session(engine=engine)
    outer_transaction = session.begin()
    session.begin_nested()

    def _get_session_override() -> Generator[SASession, None, None]:
        yield session

    app.dependency_overrides[_get_session] = _get_session_override

    try:
        with TestClient(app=app) as client:
            yield app, client, session
    finally:
        app.dependency_overrides.pop(_get_session, None)
        if outer_transaction.is_active:
            outer_transaction.rollback()
        session.close()


class TestVerifyApiKeyValid:
    """Valid API key returns 200 and updates last_used_at."""

    def test_valid_key_returns_200(self, app_and_client: tuple) -> None:
        """A valid, non-expired, non-revoked key for an active user returns 200."""
        _, client, session = app_and_client
        user = _create_user(session)
        plaintext, key_hash = _make_key()
        _create_api_key(session, user, plaintext, key_hash)

        response = client.get("/test/protected", headers={"X-API-Key": plaintext})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["user_id"] == user.id

    def test_valid_key_updates_last_used_at(self, app_and_client: tuple) -> None:
        """Successful auth updates last_used_at on the key."""
        _, client, session = app_and_client
        user = _create_user(session)
        plaintext, key_hash = _make_key()
        api_key = _create_api_key(session, user, plaintext, key_hash)

        assert api_key.last_used_at is None

        client.get("/test/protected", headers={"X-API-Key": plaintext})

        session.refresh(api_key)
        assert api_key.last_used_at is not None


class TestVerifyApiKeyRejection:
    """Invalid, expired, revoked keys and missing header return 401."""

    def test_missing_header_returns_401(self, app_and_client: tuple) -> None:
        """Request without X-API-Key header returns 401."""
        _, client, _ = app_and_client

        response = client.get("/test/protected")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_key_returns_401(self, app_and_client: tuple) -> None:
        """Non-existent key returns 401."""
        _, client, _ = app_and_client

        response = client.get("/test/protected", headers={"X-API-Key": "tbk_bogus"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_key_returns_401(self, app_and_client: tuple) -> None:
        """Expired key returns 401."""
        _, client, session = app_and_client
        user = _create_user(session)
        plaintext, key_hash = _make_key()
        _create_api_key(
            session,
            user,
            plaintext,
            key_hash,
            expires_at=datetime.now() - timedelta(days=1),  # noqa: DTZ005
        )

        response = client.get("/test/protected", headers={"X-API-Key": plaintext})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_revoked_key_returns_401(self, app_and_client: tuple) -> None:
        """Revoked key returns 401."""
        _, client, session = app_and_client
        user = _create_user(session)
        plaintext, key_hash = _make_key()
        _create_api_key(
            session,
            user,
            plaintext,
            key_hash,
            revoked_at=datetime.now(),  # noqa: DTZ005
        )

        response = client.get("/test/protected", headers={"X-API-Key": plaintext})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_returns_401(self, app_and_client: tuple) -> None:
        """Key belonging to an inactive user returns 401."""
        _, client, session = app_and_client
        user = _create_user(session, is_active=False, email="inactive@example.com")
        plaintext, key_hash = _make_key()
        _create_api_key(session, user, plaintext, key_hash)

        response = client.get("/test/protected", headers={"X-API-Key": plaintext})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestHasPermissionWithApiKey:
    """has_permission works on ApiKeyRouter endpoints."""

    def test_user_with_permission_passes(self, app_and_client: tuple) -> None:
        """API key user with required permission gets 200."""
        _, client, session = app_and_client
        user = _create_user(session, email="perm@example.com")

        perm = Permission(name="monitoring_read", creator_user_id=user.id, last_modifier_user_id=user.id)
        session.add(perm)
        session.flush()

        role = Role(name="test_role", is_active=True, creator_user_id=user.id, last_modifier_user_id=user.id)
        session.add(role)
        session.flush()

        rp = RolePermission(
            role_id=role.id, permission_id=perm.id, creator_user_id=user.id, last_modifier_user_id=user.id
        )
        session.add(rp)
        ur = UserRole(user_id=user.id, role_id=role.id, creator_user_id=user.id, last_modifier_user_id=user.id)
        session.add(ur)
        session.flush()

        plaintext, key_hash = _make_key()
        _create_api_key(session, user, plaintext, key_hash)

        response = client.get("/test/with-permission", headers={"X-API-Key": plaintext})

        assert response.status_code == status.HTTP_200_OK

    def test_user_without_permission_gets_403(self, app_and_client: tuple) -> None:
        """API key user without required permission gets 403."""
        _, client, session = app_and_client
        user = _create_user(session, email="noperm@example.com")
        plaintext, key_hash = _make_key()
        _create_api_key(session, user, plaintext, key_hash)

        response = client.get("/test/with-permission", headers={"X-API-Key": plaintext})

        assert response.status_code == status.HTTP_403_FORBIDDEN
