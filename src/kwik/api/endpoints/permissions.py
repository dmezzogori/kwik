"""Permission management API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik import crud
from kwik.api.deps import PaginatedQuery, has_permission
from kwik.core.enum import Permissions
from kwik.exceptions import DuplicatedEntity
from kwik.routers import AuditorRouter
from kwik.schemas import Paginated, PermissionCreate, PermissionORMSchema, PermissionUpdate
from kwik.typings import PaginatedResponse

if TYPE_CHECKING:
    from kwik.models import Permission

router = AuditorRouter()


@router.get(
    "/",
    response_model=Paginated[PermissionORMSchema],
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def get_many_permissions(paginated: PaginatedQuery) -> PaginatedResponse[Permission]:
    """
    Get all permissions, paginated.

    Permissions required:

     -  `permissions_management_read`
    """
    total, permissions = crud.permission.get_multi(**paginated)
    return PaginatedResponse(total=total, data=permissions)


@router.get(
    "/{permission_id}",
    response_model=PermissionORMSchema,
    dependencies=(has_permission(Permissions.permissions_management_read),),
)
def get_single_permission(permission_id: int) -> Permission:
    """
    Get a single permission by id.

    Permissions required:
        * `permissions_management_read`

    Raises:
        NotFound: If the provided permission does not exist

    """
    return crud.permission.get_if_exist(id=permission_id)


@router.post(
    "",
    response_model=PermissionORMSchema,
    dependencies=(has_permission(Permissions.permissions_management_create),),
)
def create_permission(permission_in: PermissionCreate) -> Permission:
    """
    Create new permission.

    Raises:
        DuplicatedEntity: If the provided permission name already exists

    Permissions required:
        * `permissions_management_create`

    """
    permission = crud.permission.get_by_name(name=permission_in.name)
    if permission is not None:
        raise DuplicatedEntity

    return crud.permission.create(obj_in=permission_in)


@router.post(
    "/{permission_id}/{role_id}",
    response_model=PermissionORMSchema,
    dependencies=(has_permission(Permissions.permissions_management_update),),
)
def associate_permission_to_role(permission_id: int, role_id: int) -> Permission:
    """
    Associate a permission to a role.

    Raises:
        NotFound: If the provided permission or role does not exist

    Permissions required:
        * `permissions_management_update`

    """
    return crud.permission.associate_role(permission_id=permission_id, role_id=role_id)


@router.put(
    "/{permission_id}",
    response_model=PermissionORMSchema,
    dependencies=(has_permission(Permissions.permissions_management_update),),
)
def update_permission(permission_id: int, permission_in: PermissionUpdate) -> Permission:
    """
    Update a permission.

    Raises:
        NotFound: If the provided permission does not exist

    Permissions required:
        * `permissions_management_update`

    """
    permission = crud.permission.get_if_exist(id=permission_id)
    return crud.permission.update(db_obj=permission, obj_in=permission_in)


@router.delete(
    "/{permission_id}/roles",
    response_model=PermissionORMSchema,
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
    return crud.permission.purge_all_roles(permission_id=permission_id)


@router.delete(
    "/{permission_id}/{role_id}",
    response_model=PermissionORMSchema,
    dependencies=(has_permission(Permissions.permissions_management_delete),),
)
def purge_role_from_permission(permission_id: int, role_id: int) -> Permission:
    """
    Remove permission from role.

    NotFound: If the provided permission or role does not exist
    * `permissions_management_delete`

    """
    return crud.permission.purge_role(permission_id=permission_id, role_id=role_id)


@router.delete(
    "/{permission_id}",
    response_model=PermissionORMSchema,
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
    return crud.permission.delete(id=permission_id)
