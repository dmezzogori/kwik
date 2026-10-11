"""A deactivated role is held by no one (teban #908)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.crud import crud_permissions, crud_roles, crud_users
from kwik.schemas import PermissionDefinition, RoleDefinition

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.crud import UserCtx
    from kwik.models import Permission, Role, User

PERMISSION_NAME = "inactive_role_probe"
INACTIVE_ROLE = "probe-inactive"
ACTIVE_ROLE = "probe-active"


def _permission(admin_context: UserCtx) -> Permission:
    """Create the probe permission."""
    return crud_permissions.create(obj_in=PermissionDefinition(name=PERMISSION_NAME), context=admin_context)


def _grant(admin_context: UserCtx, user: User, *, active: bool, role_name: str, permission: Permission) -> Role:
    """Give ``user`` a role carrying ``permission``, active or not."""
    role = crud_roles.create(obj_in=RoleDefinition(name=role_name, is_active=active), context=admin_context)
    crud_roles.assign_permission(role=role, permission=permission, context=admin_context)
    crud_roles.assign_user(role=role, user=user, context=admin_context)
    admin_context.session.refresh(user)
    return role


class TestInactiveRoles:
    """Every role and permission read counts active roles only."""

    def test_inactive_role_grants_nothing(self, admin_context: UserCtx, user_factory: Callable[..., User]) -> None:
        """A user whose only role is inactive holds neither the role nor its permissions."""
        user = user_factory(email="inactive-only@example.com")
        permission = _permission(admin_context)
        role = _grant(admin_context, user, active=False, role_name=INACTIVE_ROLE, permission=permission)

        assert crud_users.has_permissions(user=user, permissions=[PERMISSION_NAME]) is False
        assert crud_users.has_roles(user=user, roles=[role.name]) is False
        assert role not in crud_users.get_roles(user=user)
        assert permission not in crud_users.get_permissions(user=user)
        assert permission not in user.permissions

    def test_inactive_role_still_listed_as_assignment(
        self, admin_context: UserCtx, user_factory: Callable[..., User]
    ) -> None:
        """``User.roles`` stays the raw assignment list, so admin screens can show and remove it."""
        user = user_factory(email="inactive-assigned@example.com")
        role = _grant(admin_context, user, active=False, role_name=INACTIVE_ROLE, permission=_permission(admin_context))

        assert role in user.roles

    def test_detached_fallback_ignores_inactive_role(
        self, admin_context: UserCtx, user_factory: Callable[..., User]
    ) -> None:
        """The detached-user fallback of has_permissions filters inactive roles too."""
        user = user_factory(email="inactive-detached@example.com")
        _grant(admin_context, user, active=False, role_name=INACTIVE_ROLE, permission=_permission(admin_context))
        _ = [role.permissions for role in user.roles]  # load before detaching
        admin_context.session.expunge(user)

        assert crud_users.has_permissions(user=user, permissions=[PERMISSION_NAME]) is False

    def test_permission_via_active_and_inactive_role_kept(
        self, admin_context: UserCtx, user_factory: Callable[..., User]
    ) -> None:
        """A permission also granted by an active role is still held."""
        user = user_factory(email="inactive-and-active@example.com")
        permission = _permission(admin_context)
        _grant(admin_context, user, active=False, role_name=INACTIVE_ROLE, permission=permission)
        _grant(admin_context, user, active=True, role_name=ACTIVE_ROLE, permission=permission)

        assert crud_users.has_permissions(user=user, permissions=[PERMISSION_NAME]) is True
        assert permission in crud_users.get_permissions(user=user)

    def test_reactivation_restores(self, admin_context: UserCtx, user_factory: Callable[..., User]) -> None:
        """Reactivating the role gives its holders their permissions back."""
        user = user_factory(email="inactive-reactivated@example.com")
        role = _grant(admin_context, user, active=False, role_name=INACTIVE_ROLE, permission=_permission(admin_context))
        role.is_active = True
        admin_context.session.flush()

        assert crud_users.has_permissions(user=user, permissions=[PERMISSION_NAME]) is True
        assert role in crud_users.get_roles(user=user)
