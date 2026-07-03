"""Tests for IdentityAwareTestClient password registration."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kwik.models.user_mixin import UserMixin
    from kwik.testing import IdentityAwareTestClient


class TestRegisteredPasswords:
    """Tests for IdentityAwareTestClient.register_passwords."""

    def test_registered_password_is_used_for_login(
        self,
        identity_aware_client: IdentityAwareTestClient,
        admin_user: UserMixin,
    ) -> None:
        """A registered password authenticates a user the legacy fallback would fail to log in."""
        # Create the user through the API (as admin) so it is visible to the app session,
        # with a non-default password that the client's legacy fallbacks do not know.
        email = "custompw@test.com"
        password = "anotherpw456"
        created = identity_aware_client.post_as(
            admin_user,
            "/api/v1/users/",
            json={"name": "custompw", "surname": "user", "email": email, "password": password, "is_active": True},
        )
        assert created.status_code == HTTPStatus.OK
        user = SimpleNamespace(id=created.json()["id"], email=email)

        # Without register_passwords the fallback would send "testpassword123" and 401.
        identity_aware_client.register_passwords({email: password})
        response = identity_aware_client.get_as(user, "/api/v1/users/me")  # type: ignore[arg-type]
        assert response.status_code == HTTPStatus.OK
