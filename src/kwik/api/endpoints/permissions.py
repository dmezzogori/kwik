"""Permission management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.api.deps import Pagination, has_permission
from kwik.core.enum import Permissions
from kwik.crud import crud_permissions
from kwik.exceptions import DuplicatedEntityError
from kwik.routers import AuditorRouter
from kwik.schemas import Paginated, PermissionDefinition, PermissionProfile, PermissionRoleAssignment, PermissionUpdate
from kwik.typings import PaginatedResponse

if TYPE_CHECKING:
    from kwik.models import Permission

permissions_router = AuditorRouter(prefix="/permissions")


@permissions_router.get(
    "/",
    response_model=Paginated[PermissionProfile],
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def read_permissions(paginated: Pagination) -> PaginatedResponse[Permission]:
    """Retrieve permissions."""
    total, data = crud_permissions.get_multi(**paginated)
    return PaginatedResponse(total=total, data=data)


@permissions_router.post(
    "/",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_create),),
)
def create_permission(permission_in: PermissionDefinition) -> Permission:
    """Create new permission."""
    permission = crud_permissions.get_by_name(name=permission_in.name)
    if permission is not None:
        raise DuplicatedEntityError

    return crud_permissions.create(obj_in=permission_in)


@permissions_router.get(
    "/{permission_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def read_permission_by_id(permission_id: int) -> Permission:
    """Get a specific permission by id."""
    return crud_permissions.get_if_exist(id=permission_id)


@permissions_router.put(
    "/{permission_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_update),),
)
def update_permission(permission_id: int, permission_in: PermissionUpdate) -> Permission:
    """Update a permission."""
    permission = crud_permissions.get_if_exist(id=permission_id)
    return crud_permissions.update(db_obj=permission, obj_in=permission_in)


@permissions_router.post(
    "/{permission_id}/roles",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_update),),
)
def associate_permission_to_role(permission_id: int, assignment: PermissionRoleAssignment) -> Permission:
    """
    Associate a permission to a role.

    Raises:
        NotFound: If the provided permission or role does not exist

    Permissions required:
        * `permissions_management_update`

    """
    return crud_permissions.associate_role(permission_id=permission_id, role_id=assignment.role_id)


@permissions_router.delete(
    "/{permission_id}/roles",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_delete),),
)
def purge_all_roles(permission_id: int) -> Permission:
    """
    Remove all existing associations of a permission to any role.

    Does not delete the permission itself.

    Raises:
        NotFound: If the provided permission does not exist

    Permissions required:
        * `permissions_management_delete`

    """
    return crud_permissions.purge_all_roles(permission_id=permission_id)


@permissions_router.delete(
    "/{permission_id}/roles/{role_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_delete),),
)
def purge_role_from_permission(permission_id: int, role_id: int) -> Permission:
    """
    Remove permission from role.

    Raises:
        NotFound: If the provided permission or role does not exist

    Permissions required:
        * `permissions_management_delete`

    """
    return crud_permissions.purge_role(permission_id=permission_id, role_id=role_id)


@permissions_router.delete(
    "/{permission_id}",
    response_model=PermissionProfile,
    dependencies=(has_permission(Permissions.permissions_management_delete),),
)
def delete_permission(permission_id: int) -> Permission:
    """
    Delete a permission and remove all existing associations of it to any role.

    Raises:
        NotFound: If the provided permission does not exist

    Permissions required:
        * `permissions_management_delete`

    """
    return crud_permissions.delete(id=permission_id)


__all__ = ["permissions_router"]
