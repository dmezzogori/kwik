"""Through the API, a deactivated role is held by no one (teban #908)."""

from __future__ import annotations

from http import HTTPStatus
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from kwik.core.enum import Permissions

if TYPE_CHECKING:
    from kwik.models import User
    from kwik.testing import IdentityAwareTestClient

API = "/api/v1"
ROLE_NAME = "probe-inactive-reader"
EMAIL = "inactive-role-holder@example.com"
PASSWORD = "testpassword123"
PAGE_LIMIT = 100


def _setup_inactive_reader(client: IdentityAwareTestClient, admin_user: User) -> User:
    """Create a user whose only role, inactive, carries ``user_read``."""
    created = client.post_as(
        admin_user,
        f"{API}/users/",
        json={"name": "probe", "surname": "probe", "email": EMAIL, "password": PASSWORD, "is_active": True},
    )
    assert created.status_code == HTTPStatus.OK
    role = client.post_as(admin_user, f"{API}/roles/", json={"name": ROLE_NAME, "is_active": False})
    assert role.status_code == HTTPStatus.OK
    role_id = role.json()["id"]

    permissions = client.get_as(admin_user, f"{API}/permissions/?limit={PAGE_LIMIT}").json()["data"]
    user_read = next(p for p in permissions if p["name"] == Permissions.user_read.value)
    assigned = client.post_as(admin_user, f"{API}/roles/{role_id}/permissions", json={"permission_id": user_read["id"]})
    assert assigned.status_code == HTTPStatus.OK
    joined = client.post_as(admin_user, f"{API}/roles/{role_id}/users", json={"user_id": created.json()["id"]})
    assert joined.status_code == HTTPStatus.OK
    return cast("User", SimpleNamespace(id=created.json()["id"], email=EMAIL))


class TestInactiveRolesRouter:
    """The /me reads and the permission gates ignore inactive roles."""

    def test_me_roles_omits_inactive_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """``GET /users/me/roles`` does not list an inactive role."""
        user = _setup_inactive_reader(identity_aware_client, admin_user)
        response = identity_aware_client.get_as(user, f"{API}/users/me/roles")
        assert response.status_code == HTTPStatus.OK
        assert ROLE_NAME not in [role["name"] for role in response.json()]

    def test_me_permissions_omits_inactive_roles_permissions(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """``GET /users/me/permissions`` does not list what only an inactive role grants."""
        user = _setup_inactive_reader(identity_aware_client, admin_user)
        response = identity_aware_client.get_as(user, f"{API}/users/me/permissions")
        assert response.status_code == HTTPStatus.OK
        assert Permissions.user_read.value not in [permission["name"] for permission in response.json()]

    def test_permission_gate_refuses(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """A route gated on ``user_read`` refuses a user who holds it only through an inactive role."""
        user = _setup_inactive_reader(identity_aware_client, admin_user)
        assert identity_aware_client.get_as(user, f"{API}/users/").status_code == HTTPStatus.FORBIDDEN
