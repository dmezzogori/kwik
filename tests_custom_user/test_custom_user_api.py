"""API behavior: registered schemas bind to request bodies and response models."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kwik.models import UserMixin
    from kwik.testing import IdentityAwareTestClient


class TestCustomUserApi:
    """API coverage: the custom schemas bind to request bodies and response models."""

    def test_me_exposes_custom_field(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: UserMixin
    ) -> None:
        """The /users/me response model exposes the custom column."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/me")
        assert response.status_code == HTTPStatus.OK
        assert "nickname" in response.json()

    def test_create_user_accepts_custom_field(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: UserMixin
    ) -> None:
        """The create-user endpoint accepts and echoes the custom column."""
        payload = {
            "name": "nova",
            "surname": "Custom",
            "email": "nova@test.com",
            "password": "novapassword123",
            "nickname": "Nova",
        }
        response = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=payload)
        assert response.status_code == HTTPStatus.OK
        assert response.json()["nickname"] == "Nova"
