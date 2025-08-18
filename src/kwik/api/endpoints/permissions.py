"""Permission management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.crud import crud_permissions
from kwik.dependencies import ListQuery, UserContext, has_permission
from kwik.exceptions import DuplicatedEntityError
from kwik.routers import AuthenticatedRouter
from kwik.schemas import Paginated, PermissionDefinition, PermissionProfile, PermissionUpdate, RoleProfile

if TYPE_CHECKING:
    from kwik.models import Permission, Role

permissions_router = AuthenticatedRouter(prefix="/permissions")


@permissions_router.get(
    "/",
    response_model=Paginated[PermissionProfile],
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def read_permissions(q: ListQuery, context: UserContext) -> Paginated[PermissionProfile]:
    """Retrieve permissions."""
    total, data = crud_permissions.get_multi(context=context, **q)
    return {"total": total, "data": data}


@permissions_router.post(
    "/",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_create),),
)
def create_permission(permission_in: PermissionDefinition, context: UserContext) -> Permission:
    """Create new permission."""
    permission = crud_permissions.get_by_name(name=permission_in.name, context=context)
    if permission is not None:
        raise DuplicatedEntityError

    return crud_permissions.create(obj_in=permission_in, context=context)


@permissions_router.get(
    "/{permission_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def read_permission_by_id(permission_id: int, context: UserContext) -> Permission:
    """Get a specific permission by id."""
    return crud_permissions.get_if_exist(entity_id=permission_id, context=context)


@permissions_router.put(
    "/{permission_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_update),),
)
def update_permission(permission_id: int, permission_in: PermissionUpdate, context: UserContext) -> Permission:
    """Update a permission."""
    return crud_permissions.update(entity_id=permission_id, obj_in=permission_in, context=context)


@permissions_router.get(
    "/{permission_id}/roles",
    response_model=list[RoleProfile],
    dependencies=(
        has_permission(
            Permissions.permissions_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def read_roles_by_permission(permission_id: int, context: UserContext) -> list[Role]:
    """Get roles associated to a permission."""
    permission = crud_permissions.get_if_exist(entity_id=permission_id, context=context)
    return crud_permissions.get_roles_assigned_to(permission=permission)


@permissions_router.get(
    "/{permission_id}/available-roles",
    response_model=list[RoleProfile],
    dependencies=(
        has_permission(
            Permissions.permissions_management_read,
            Permissions.roles_management_read,
        ),
    ),
)
def read_available_roles_for_permission(permission_id: int, context: UserContext) -> list[Role]:
    """Get all roles available to assign to the given permission."""
    permission = crud_permissions.get_if_exist(entity_id=permission_id, context=context)
    return crud_permissions.get_roles_assignable_to(permission=permission, context=context)


@permissions_router.delete(
    "/{permission_id}/roles",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_delete),),
)
def purge_all_roles(permission_id: int, context: UserContext) -> Permission:
    """
    Remove all existing associations of a permission to any role.

    Does not delete the permission itself.

    Raises:
        NotFound: If the provided permission does not exist

    Permissions required:
        * `permissions_management_delete`

    """
    return crud_permissions.purge_all_roles(permission_id=permission_id, context=context)


@permissions_router.delete(
    "/{permission_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_delete),),
)
def delete_permission(permission_id: int, context: UserContext) -> Permission:
    """
    Delete a permission and remove all existing associations of it to any role.

    Raises:
        NotFound: If the provided permission does not exist

    Permissions required:
        * `permissions_management_delete`

    """
    return crud_permissions.delete(entity_id=permission_id, context=context)


__all__ = ["permissions_router"]
