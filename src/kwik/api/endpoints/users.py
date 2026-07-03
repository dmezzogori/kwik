"""User management API endpoints (kernel-bound factory)."""

# NOTE: no `from __future__ import annotations` — request/response schemas are
# resolved from the kernel at factory-call time and must evaluate eagerly.

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.dependencies import ListQuery, UserContext, current_user, has_permission
from kwik.exceptions import DuplicatedEntityError
from kwik.models.user_mixin import UserMixin
from kwik.routers import AuthenticatedRouter
from kwik.schemas import AdminPasswordReset, Paginated, PermissionProfile, RoleProfile, UserPasswordChange

if TYPE_CHECKING:
    from kwik.kernel import Kernel
    from kwik.models import Permission, Role


def create_users_router(kernel: "Kernel[UserMixin]") -> AuthenticatedRouter:  # noqa: C901
    """Build the /users router bound to the kernel's registered model and schemas."""
    crud_users = kernel.crud_users
    profile_schema = kernel.schemas.profile
    registration_schema = kernel.schemas.registration
    update_schema = kernel.schemas.update

    router = AuthenticatedRouter(prefix="/users")

    @router.get("/", response_model=Paginated[profile_schema], dependencies=(has_permission(Permissions.user_read),))
    def read_users(q: ListQuery, context: UserContext) -> dict[str, object]:
        """Retrieve users."""
        total, data = crud_users.get_multi(context=context, **q)
        return {"total": total, "data": data}

    @router.post("/", response_model=profile_schema, dependencies=(has_permission(Permissions.user_create),))
    def create_user(user_in: registration_schema, context: UserContext) -> UserMixin:
        """Create new user."""
        user = crud_users.get_by_email(email=user_in.email, context=context)
        if user:
            raise DuplicatedEntityError

        return crud_users.create(obj_in=user_in, context=context)

    @router.get("/me", response_model=profile_schema)
    def read_user_me(user: current_user) -> UserMixin:
        """Get current user."""
        return user

    @router.put("/me", response_model=profile_schema)
    def update_myself(user: current_user, user_in: update_schema, context: UserContext) -> UserMixin:
        """Update details of the logged in user."""
        return crud_users.update(entity_id=user.id, obj_in=user_in, context=context)

    @router.get("/me/permissions", response_model=list[PermissionProfile])
    def read_permissions_of_current_user(user: current_user) -> "list[Permission]":
        """Get all effective permissions of the current logged-in user."""
        return crud_users.get_permissions(user=user)

    @router.get("/me/roles", response_model=list[RoleProfile])
    def read_roles_of_current_user(user: current_user) -> "list[Role]":
        """Get roles of the current logged-in user."""
        return crud_users.get_roles(user=user)

    @router.put("/me/password", response_model=profile_schema)
    def update_my_password(user: current_user, obj_in: UserPasswordChange, context: UserContext) -> UserMixin:
        """Update current user's password."""
        return crud_users.change_password(user_id=user.id, obj_in=obj_in, context=context)

    @router.get("/{user_id}", response_model=profile_schema, dependencies=(has_permission(Permissions.user_read),))
    def read_user_by_id(user_id: int, context: UserContext) -> UserMixin:
        """Get a specific user by id."""
        return crud_users.get_if_exist(entity_id=user_id, context=context)

    @router.put("/{user_id}", response_model=profile_schema, dependencies=(has_permission(Permissions.user_update),))
    def update_user(user_id: int, user_in: update_schema, context: UserContext) -> UserMixin:
        """Update a user."""
        return crud_users.update(entity_id=user_id, obj_in=user_in, context=context)

    @router.get(
        "/{user_id}/permissions",
        response_model=list[PermissionProfile],
        dependencies=(
            has_permission(Permissions.user_read),
            has_permission(Permissions.permission_read),
        ),
    )
    def read_user_permissions(user_id: int, context: UserContext) -> "list[Permission]":
        """Get all effective permissions for a specific user."""
        user = crud_users.get_if_exist(entity_id=user_id, context=context)
        return crud_users.get_permissions(user=user)

    @router.get(
        "/{user_id}/roles",
        response_model=list[RoleProfile],
        dependencies=(
            has_permission(
                Permissions.user_read,
                Permissions.role_read,
            ),
        ),
    )
    def read_user_roles(user_id: int, context: UserContext) -> "list[Role]":
        """Get all roles assigned to a specific user."""
        user = crud_users.get_if_exist(entity_id=user_id, context=context)
        return crud_users.get_roles(user=user)

    @router.put(
        "/{user_id}/password",
        response_model=profile_schema,
        dependencies=(has_permission(Permissions.user_update),),
    )
    def update_password(user_id: int, obj_in: UserPasswordChange, context: UserContext) -> UserMixin:
        """Update user's password (admin operation)."""
        return crud_users.change_password(user_id=user_id, obj_in=obj_in, context=context)

    @router.put(
        "/{user_id}/reset-password",
        response_model=profile_schema,
        dependencies=(has_permission(Permissions.password_reset),),
    )
    def admin_reset_password(user_id: int, obj_in: AdminPasswordReset, context: UserContext) -> UserMixin:
        """Reset user's password (admin operation, no old password required)."""
        return crud_users.admin_reset_password(user_id=user_id, password=obj_in.new_password, context=context)

    return router


__all__ = ["create_users_router"]
