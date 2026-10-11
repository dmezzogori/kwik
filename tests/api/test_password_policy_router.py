"""Every endpoint that sets a password enforces the minimum length (teban #302)."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from kwik.core import DEFAULT_PASSWORD_MIN_LENGTH

if TYPE_CHECKING:
    from starlette.testclient import TestClient

    from kwik.models import User
    from kwik.testing import IdentityAwareTestClient

API = "/api/v1"
SHORT = "a" * (DEFAULT_PASSWORD_MIN_LENGTH - 1)
LONG_ENOUGH = "b" * DEFAULT_PASSWORD_MIN_LENGTH


def _registration(email: str, password: str) -> dict[str, object]:
    """User creation payload."""
    return {"name": "p", "surname": "p", "email": email, "password": password, "is_active": True}


class TestPasswordPolicyRouter:
    """Short new passwords are a 422 on every route that sets one."""

    def test_create_user(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """``POST /users/`` refuses a short password and accepts one of the minimum length."""
        short = identity_aware_client.post_as(admin_user, f"{API}/users/", json=_registration("s@example.com", SHORT))
        assert short.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        ok = identity_aware_client.post_as(
            admin_user, f"{API}/users/", json=_registration("l@example.com", LONG_ENOUGH)
        )
        assert ok.status_code == HTTPStatus.OK

    def test_change_own_password(self, identity_aware_client: IdentityAwareTestClient, regular_user: User) -> None:
        """``PUT /users/me/password`` refuses a short new password."""
        response = identity_aware_client.put_as(
            regular_user,
            f"{API}/users/me/password",
            json={"old_password": "regularpassword123", "new_password": SHORT},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_change_password_by_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """``PUT /users/{id}/password`` refuses a short new password."""
        response = identity_aware_client.put_as(
            admin_user,
            f"{API}/users/{regular_user.id}/password",
            json={"old_password": "regularpassword123", "new_password": SHORT},
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_admin_reset(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """``PUT /users/{id}/reset-password`` refuses a short new password."""
        response = identity_aware_client.put_as(
            admin_user, f"{API}/users/{regular_user.id}/reset-password", json={"new_password": SHORT}
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_token_reset(self, client: TestClient) -> None:
        """``POST /login/reset-password`` refuses a short password before looking at the token."""
        response = client.post(f"{API}/login/reset-password", json={"token": "irrelevant", "password": SHORT})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_admin_seeded_with_short_password_can_log_in(self, client: TestClient, settings: object) -> None:
        """The development superuser, seeded with "admin" through the bypass, still signs in."""
        response = client.post(
            f"{API}/login/access-token",
            data={"username": settings.FIRST_SUPERUSER, "password": settings.FIRST_SUPERUSER_PASSWORD},  # type: ignore[attr-defined]
        )
        assert response.status_code == HTTPStatus.OK
