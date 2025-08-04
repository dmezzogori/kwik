"""Role management API endpoints."""

from __future__ import annotations

import kwik.api.deps
import kwik.typings
from kwik import crud, models, schemas
from kwik.core.enum import Permissions
from kwik.exceptions import DuplicatedEntity
from kwik.routers import AuditorRouter

router = AuditorRouter(prefix="/roles")


@router.get(
    "/",
    response_model=schemas.Paginated[schemas.RoleProfile],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_roles(paginated: kwik.api.deps.Pagination) -> kwik.typings.PaginatedResponse[models.Role]:
    """Retrieve roles."""
    count, roles = crud.roles.get_multi(**paginated)
    return kwik.typings.PaginatedResponse(data=roles, total=count)


@router.get(
    "/{role_id}/users",
    response_model=schemas.Paginated[schemas.UserProfile],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_users_by_role(role_id: int) -> kwik.typings.PaginatedResponse[models.User]:
    """Get users by role."""
    users = crud.roles.get_users_by_role_id(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=users, total=len(users))


@router.get(
    "/{role_id}/assignable-users",
    response_model=schemas.Paginated[schemas.UserProfile],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_users_not_in_role(role_id: int) -> kwik.typings.PaginatedResponse[models.User]:
    """Get all users not involved in the given role."""
    users = crud.roles.get_users_not_in_role(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=users, total=len(users))


@router.get(
    "/{role_id}/permissions",
    response_model=schemas.Paginated[schemas.PermissionProfile],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_permissions_by_role(role_id: int) -> kwik.typings.PaginatedResponse[models.Permission]:
    """Get permissions by role."""
    permissions = crud.roles.get_permissions_by_role_id(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=permissions, total=len(permissions))


@router.get(
    "/{role_id}/assignable-permissions",
    response_model=schemas.Paginated[schemas.PermissionProfile],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_permissions_not_assigned_to_role(role_id: int) -> kwik.typings.PaginatedResponse[models.Permission]:
    """Get all permissions not assigned to the given role."""
    permissions = crud.roles.get_permissions_not_assigned_to_role(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=permissions, total=len(permissions))


@router.get(
    "/{role_id}",
    response_model=schemas.RoleProfile,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_role_by_id(role_id: int) -> models.Role:
    """Get a specific role by id."""
    return crud.roles.get(id=role_id)


@router.put(
    "/{role_id}",
    response_model=schemas.RoleProfile,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_update),),
)
def update_role(role_id: int, role_in: schemas.RoleUpdate) -> models.Role:
    """Update a role."""
    role = crud.roles.get_if_exist(id=role_id)
    return crud.roles.update(db_obj=role, obj_in=role_in)


@router.post(
    "",
    response_model=schemas.RoleProfile,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_create),),
)
def create_role(role_in: schemas.RoleDefinition) -> models.Role:
    """Create new role."""
    role = crud.roles.get_by_name(name=role_in.name)
    if role is not None:
        raise DuplicatedEntity

    return crud.roles.create(obj_in=role_in)


@router.delete(
    "/{role_id}",
    response_model=schemas.RoleProfile,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_delete),),
)
def delete_role(role_id: int) -> models.Role:
    """Delete a role."""
    crud.roles.get_if_exist(id=role_id)
    return crud.roles.remove(id=role_id)


@router.delete(
    "/{name}/deprecate",
    response_model=schemas.RoleProfile,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_delete),),
)
def deprecate_role_by_name(name: str) -> models.Role:
    """Deprecate role. Remove all associated users."""
    return crud.roles.deprecate(name=name)
