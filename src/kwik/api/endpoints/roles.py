"""Role management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import kwik.typings
from kwik.api.deps import Pagination, has_permission
from kwik.core.enum import Permissions
from kwik.crud import crud_roles
from kwik.exceptions import DuplicatedEntityError
from kwik.routers import AuditorRouter
from kwik.schemas import Paginated, PermissionProfile, RoleDefinition, RoleProfile, RoleUpdate, UserProfile

if TYPE_CHECKING:
    from kwik.models import Permission, Role, User

roles_router = AuditorRouter(prefix="/roles")


@roles_router.get(
    "/",
    response_model=Paginated[RoleProfile],
    dependencies=(has_permission(Permissions.roles_management_read),),
)
def read_roles(paginated: Pagination) -> kwik.typings.PaginatedResponse[Role]:
    """Retrieve roles."""
    total, data = crud_roles.get_multi(**paginated)
    return kwik.typings.PaginatedResponse(data=data, total=total)


@roles_router.post(
    "/",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_create),),
)
def create_role(role_in: RoleDefinition) -> Role:
    """Create new role."""
    role = crud_roles.get_by_name(name=role_in.name)
    if role is not None:
        raise DuplicatedEntityError

    return crud_roles.create(obj_in=role_in)


@roles_router.get(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_read),),
)
def read_role_by_id(role_id: int) -> Role:
    """Get a specific role by id."""
    return crud_roles.get_if_exist(id=role_id)


@roles_router.put(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_update),),
)
def update_role(role_id: int, role_in: RoleUpdate) -> Role:
    """Update a role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.update(db_obj=role, obj_in=role_in)


@roles_router.delete(
    "/{role_id}",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_delete),),
)
def delete_role(role_id: int) -> Role:
    """Delete a role."""
    crud_roles.get_if_exist(id=role_id)
    return crud_roles.delete(id=role_id)


@roles_router.get(
    "/{role_id}/permissions/assigned",
    response_model=list[PermissionProfile],
    dependencies=(
        has_permission(
            Permissions.roles_management_read,
            Permissions.permissions_management_read,
        ),
    ),
)
def read_permissions_by_role(role_id: int) -> list[Permission]:
    """Get permissions associated to a role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.get_permissions_assigned_to(role=role)


@roles_router.get(
    "/{role_id}/permissions/not-assigned",
    response_model=list[PermissionProfile],
    dependencies=(
        has_permission(
            Permissions.roles_management_read,
            Permissions.permissions_management_read,
        ),
    ),
)
def read_permissions_not_assigned_to_role(role_id: int) -> list[Permission]:
    """Get all permissions not assigned to the given role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.get_permissions_assignable_to(role=role)


@roles_router.get(
    "/{role_id}/users/assigned",
    response_model=list[UserProfile],
    dependencies=(
        has_permission(
            Permissions.users_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def users_with_role(role_id: int) -> list[User]:
    """Get users associated to a role."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.get_users_with(role=role)


@roles_router.get(
    "/{role_id}/users/not-assigned",
    response_model=list[UserProfile],
    dependencies=(
        has_permission(
            Permissions.users_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def users_without_role(role_id: int) -> list[User]:
    """Get users not associated to a role."""
    return crud_roles.get_users_without(role_id=role_id)


@roles_router.delete(
    "/{role_id}/deprecate",
    response_model=RoleProfile,
    dependencies=(has_permission(Permissions.roles_management_delete),),
)
def deprecate_role(role_id: int) -> Role:
    """Deprecate role. Remove all associated users."""
    role = crud_roles.get_if_exist(id=role_id)
    return crud_roles.deprecate(role=role)


__all__ = ["roles_router"]
