"""
Test module for login API endpoints.

This module contains comprehensive test cases for the login router endpoints including:
- OAuth2 token authentication (/access-token)
- Token validation (/test-token)
- User impersonation functionality (/impersonate, /is_impersonating, /stop_impersonating)
- Password reset functionality (/reset-password)
- Auth sessions (login opens a session, /refresh rotates it, /logout revokes it)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import jwt

from kwik.security import decode_token, generate_password_reset_token, get_password_hash

if TYPE_CHECKING:
    import pytest
    from fastapi.testclient import TestClient

    from kwik.auth import InMemoryAuthSessionStore
    from kwik.models import User
    from kwik.settings import BaseKwikSettings
    from kwik.testing import IdentityAwareTestClient

# Constants for magic values
MIN_JWT_TOKEN_LENGTH = 50
SECONDS_PER_MINUTE = 60
NO_GRACE_SECONDS = 0
LOGIN_URL = "/api/v1/login/access-token"
REFRESH_URL = "/api/v1/login/refresh"
LOGOUT_URL = "/api/v1/login/logout"
TEST_TOKEN_URL = "/api/v1/login/test-token"


def _login(client: TestClient, settings: BaseKwikSettings) -> dict:
    """Log the first superuser in with the password form and return the token response."""
    response = client.post(
        LOGIN_URL,
        data={"username": settings.FIRST_SUPERUSER, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK
    return response.json()


def _bearer(token: str) -> dict[str, str]:
    """Return the Authorization header for ``token``."""
    return {"Authorization": f"Bearer {token}"}


def _reuse(client: TestClient, settings: BaseKwikSettings, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, dict]:
    """
    Rotate a session's refresh token, then present the rotated one again outside the grace window.

    The window is set to zero instead of sleeping. Returns the first pair and the successor pair.
    """
    first = _login(client, settings)
    rotated = client.post(REFRESH_URL, json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == HTTPStatus.OK
    monkeypatch.setattr(settings, "REFRESH_REUSE_GRACE_SECONDS", NO_GRACE_SECONDS)
    reused = client.post(REFRESH_URL, json={"refresh_token": first["refresh_token"]})
    assert reused.status_code == HTTPStatus.UNAUTHORIZED
    return first, rotated.json()


class TestLoginRouter:
    """Test cases for login router API endpoints."""

    def test_access_token_valid_credentials(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/v1/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > MIN_JWT_TOKEN_LENGTH  # Basic JWT length check

    def test_access_token_invalid_email(self, client: TestClient) -> None:
        """Test login with invalid email."""
        response = client.post(
            "/api/v1/login/access-token",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_access_token_invalid_password(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_login_refused_for_inactive_user_with_the_wrong_password_answer(
        self, identity_aware_client: IdentityAwareTestClient, client: TestClient, admin_user: User
    ) -> None:
        """An inactive account with the right password gets the same answer as a wrong password."""
        email = "inactive-login@example.com"
        password = "inactivepassword123"
        created = identity_aware_client.post_as(
            admin_user,
            "/api/v1/users/",
            json={"name": "Inactive", "surname": "User", "email": email, "password": password, "is_active": False},
        )
        assert created.status_code == HTTPStatus.OK
        client.headers = {}

        refused = client.post("/api/v1/login/access-token", data={"username": email, "password": password})
        wrong = client.post("/api/v1/login/access-token", data={"username": email, "password": "wrong-password"})

        assert refused.status_code == wrong.status_code == HTTPStatus.UNAUTHORIZED
        assert refused.json() == wrong.json()

    def test_test_token_valid_token(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, settings: BaseKwikSettings
    ) -> None:
        """Test token validation with valid token."""
        response = identity_aware_client.post_as(admin_user, "/api/v1/login/test-token")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["email"] == settings.FIRST_SUPERUSER

    def test_test_token_invalid_token(self, client: TestClient) -> None:
        """Test token validation with invalid token."""
        client.headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/v1/login/test-token")

        # An invalid bearer token is a 401 with the RFC 6750 invalid_token challenge
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'

    def test_test_token_missing_token(self, client: TestClient) -> None:
        """Test token validation without token."""
        response = client.post("/api/v1/login/test-token")

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_impersonate_with_permission(
        self,
        legacy_client: TestClient,
        regular_user: User,
        settings: BaseKwikSettings,
    ) -> None:
        """
        Test successful user impersonation with proper permissions.

        Impersonation does not open sessions yet, so this runs on the application without a store.
        """
        # Login as admin with impersonation permission
        login_response = legacy_client.post(
            "/api/v1/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )
        assert login_response.status_code == HTTPStatus.OK
        admin_token = login_response.json()["access_token"]

        # Impersonate regular user
        legacy_client.headers = {**legacy_client.headers, "Authorization": f"Bearer {admin_token}"}
        response = legacy_client.post(
            "/api/v1/login/impersonate",
            params={"user_id": regular_user.id},
        )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify impersonation token works
        impersonation_token = data["access_token"]
        legacy_client.headers = {"Authorization": f"Bearer {impersonation_token}"}
        test_response = legacy_client.post("/api/v1/login/test-token")
        assert test_response.status_code == HTTPStatus.OK
        user_data = test_response.json()
        assert user_data["id"] == regular_user.id

    def test_impersonate_without_permission(
        self,
        client: TestClient,
        regular_user: User,
    ) -> None:
        """Test impersonation fails without proper permissions."""
        # Login as regular user without impersonation permissions
        login_response = client.post(
            "/api/v1/login/access-token",
            data={
                "username": regular_user.email,
                "password": "regularpassword123",
            },
        )
        user_token = login_response.json()["access_token"]

        client.headers = {"Authorization": f"Bearer {user_token}"}
        response = client.post(
            "/api/v1/login/impersonate",
            params={"user_id": regular_user.id},
        )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_impersonate_nonexistent_user(
        self,
        client: TestClient,
        settings: BaseKwikSettings,
    ) -> None:
        """Test impersonation of non-existent user."""
        # Login as admin with impersonation permission
        login_response = client.post(
            "/api/v1/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )
        admin_token = login_response.json()["access_token"]

        client.headers = {"Authorization": f"Bearer {admin_token}"}
        nonexistent_user_id = 99999
        response = client.post(
            "/api/v1/login/impersonate",
            params={"user_id": nonexistent_user_id},
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_is_impersonating_regular_token(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test is_impersonating returns False for regular token."""
        response = identity_aware_client.post_as(admin_user, "/api/v1/login/is_impersonating")

        assert response.status_code == HTTPStatus.OK
        assert response.json() is False

    def test_is_impersonating_impersonation_token(
        self,
        legacy_client: TestClient,
        regular_user: User,
        settings: BaseKwikSettings,
    ) -> None:
        """
        Test is_impersonating returns True for impersonation token.

        Impersonation does not open sessions yet, so this runs on the application without a store.
        """
        # Login and impersonate
        login_response = legacy_client.post(
            "/api/v1/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )
        admin_token = login_response.json()["access_token"]

        legacy_client.headers = {**legacy_client.headers, "Authorization": f"Bearer {admin_token}"}
        impersonate_response = legacy_client.post(
            "/api/v1/login/impersonate",
            params={"user_id": regular_user.id},
        )

        impersonation_token = impersonate_response.json()["access_token"]

        # Check impersonation status
        legacy_client.headers = {"Authorization": f"Bearer {impersonation_token}"}
        response = legacy_client.post("/api/v1/login/is_impersonating")

        assert response.status_code == HTTPStatus.OK
        assert response.json() is True

    def test_stop_impersonating(
        self,
        legacy_client: TestClient,
        regular_user: User,
        settings: BaseKwikSettings,
    ) -> None:
        """
        Test stopping impersonation and returning to original user.

        Impersonation does not open sessions yet, so this runs on the application without a store.
        """
        # Login and impersonate
        login_response = legacy_client.post(
            "/api/v1/login/access-token",
            data={
                "username": settings.FIRST_SUPERUSER,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )
        admin_token = login_response.json()["access_token"]

        legacy_client.headers = {"Authorization": f"Bearer {admin_token}"}
        impersonate_response = legacy_client.post(
            "/api/v1/login/impersonate",
            params={"user_id": regular_user.id},
        )
        impersonation_token = impersonate_response.json()["access_token"]

        # Stop impersonating
        legacy_client.headers = {"Authorization": f"Bearer {impersonation_token}"}
        stop_response = legacy_client.post("/api/v1/login/stop_impersonating")

        assert stop_response.status_code == HTTPStatus.OK
        data = stop_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify we're back to the original admin user
        original_token = data["access_token"]
        legacy_client.headers = {"Authorization": f"Bearer {original_token}"}
        test_response = legacy_client.post("/api/v1/login/test-token")
        user_data = test_response.json()
        assert user_data["email"] == settings.FIRST_SUPERUSER

    def test_stop_impersonating_regular_token(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test stop_impersonating with regular (non-impersonation) token."""
        # Regular tokens have empty kwik_impersonate field, which should return HTTP 400
        response = identity_aware_client.post_as(admin_user, "/api/v1/login/stop_impersonating")
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "invalid literal for int()" in response.json()["detail"]

    def test_reset_password_unauthenticated_valid_token(
        self,
        client: TestClient,
        regular_user: User,
        settings: BaseKwikSettings,
    ) -> None:
        """Reset password works with NO Authorization header (unauthenticated)."""
        reset_token = generate_password_reset_token(
            email=regular_user.email,
            settings=settings,
            password_hash=regular_user.hashed_password,
        )
        # Explicitly ensure the client carries no auth header.
        client.headers = {}

        response = client.post(
            "/api/v1/login/reset-password",
            json={"token": reset_token, "password": "newpassword123"},
        )

        assert response.status_code == HTTPStatus.OK
        assert response.json()["msg"] == "Password updated successfully"

    def test_reset_password_invalid_token(self, client: TestClient) -> None:
        """Test password reset with invalid token."""
        response = client.post(
            "/api/v1/login/reset-password",
            json={
                "token": "invalid_token",
                "password": "newpassword123",
            },
        )

        # Invalid JWT tokens cause TokenValidationError which returns 400
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_reset_password_expired_token(
        self, client: TestClient, regular_user: User, settings: BaseKwikSettings
    ) -> None:
        """Test password reset with expired token."""
        # Create token that expired 1 hour ago
        expired_time = datetime.now(tz=UTC) - timedelta(hours=1)
        expired_token = jwt.encode(
            {
                "exp": expired_time.timestamp(),
                "sub": regular_user.email,
                "pwd": get_password_hash("anything")[:16],
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        response = client.post(
            "/api/v1/login/reset-password",
            json={
                "token": expired_token,
                "password": "newpassword123",
            },
        )

        # Expired tokens cause TokenValidationError which returns 400
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_access_token_opens_session(
        self, client: TestClient, settings: BaseKwikSettings, auth_store: InMemoryAuthSessionStore
    ) -> None:
        """Password login opens a session and returns an access and a refresh token bound to it."""
        data = _login(client, settings)

        payload = decode_token(token=data["access_token"], settings=settings)
        assert payload.sid is not None
        assert auth_store.get(payload.sid) is not None
        assert data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * SECONDS_PER_MINUTE
        refresh_payload = decode_token(token=data["refresh_token"], settings=settings, token_type="refresh")
        assert refresh_payload.sid == payload.sid

    def test_access_token_legacy_app_has_no_session(
        self, legacy_client: TestClient, settings: BaseKwikSettings
    ) -> None:
        """Without a store, login returns a 1.13 token: no refresh token, no expires_in, no sid."""
        data = _login(legacy_client, settings)

        assert data["refresh_token"] is None
        assert data["expires_in"] is None
        assert decode_token(token=data["access_token"], settings=settings).sid is None

    def test_refresh_returns_new_pair(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """Refreshing rotates the refresh token and the new access token authenticates."""
        first = _login(client, settings)

        second = client.post(REFRESH_URL, json={"refresh_token": first["refresh_token"]})

        assert second.status_code == HTTPStatus.OK
        assert second.json()["refresh_token"] != first["refresh_token"]
        used = client.post(TEST_TOKEN_URL, headers=_bearer(second.json()["access_token"]))
        assert used.status_code == HTTPStatus.OK

    def test_refresh_rejects_access_token(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """An access token is not a refresh token."""
        first = _login(client, settings)

        response = client.post(REFRESH_URL, json={"refresh_token": first["access_token"]})

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'

    def test_refresh_reuse_revokes_session(
        self,
        client: TestClient,
        settings: BaseKwikSettings,
        auth_store: InMemoryAuthSessionStore,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Presenting a rotated refresh token outside the grace window revokes the session."""
        first, _ = _reuse(client, settings, monkeypatch)

        session_id = decode_token(token=first["access_token"], settings=settings).sid
        record = auth_store.get(session_id)
        assert record is not None
        assert record.revoked_at is not None

    def test_access_token_rejected_after_reuse(
        self, client: TestClient, settings: BaseKwikSettings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After reuse revokes the session, the successor's access token no longer authenticates."""
        _, second = _reuse(client, settings, monkeypatch)

        response = client.post(TEST_TOKEN_URL, headers=_bearer(second["access_token"]))

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_refresh_within_grace_returns_same_successor(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """The previous refresh token, presented again inside the grace window, returns the same successor."""
        first = _login(client, settings)
        second = client.post(REFRESH_URL, json={"refresh_token": first["refresh_token"]})

        again = client.post(REFRESH_URL, json={"refresh_token": first["refresh_token"]})

        assert again.status_code == HTTPStatus.OK
        assert again.json()["refresh_token"] == second.json()["refresh_token"]

    def test_refresh_without_store_is_501(self, legacy_client: TestClient) -> None:
        """An application with no session store answers 501 on refresh."""
        response = legacy_client.post(REFRESH_URL, json={"refresh_token": "anything"})

        assert response.status_code == HTTPStatus.NOT_IMPLEMENTED

    def test_logout_revokes_session(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """Logging out revokes the session: neither its access token nor its refresh token works."""
        data = _login(client, settings)

        logout = client.post(LOGOUT_URL, headers=_bearer(data["access_token"]))

        assert logout.status_code == HTTPStatus.OK
        assert logout.json() == {"msg": "Session revoked"}
        used = client.post(TEST_TOKEN_URL, headers=_bearer(data["access_token"]))
        assert used.status_code == HTTPStatus.UNAUTHORIZED
        refreshed = client.post(REFRESH_URL, json={"refresh_token": data["refresh_token"]})
        assert refreshed.status_code == HTTPStatus.UNAUTHORIZED

    def test_logout_without_store_is_501(self, legacy_client: TestClient, settings: BaseKwikSettings) -> None:
        """An application with no session store answers 501 on logout."""
        data = _login(legacy_client, settings)

        response = legacy_client.post(LOGOUT_URL, headers=_bearer(data["access_token"]))

        assert response.status_code == HTTPStatus.NOT_IMPLEMENTED
