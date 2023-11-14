from __future__ import annotations

import kwik.api.deps
import kwik.typings
from kwik import crud, models, schemas
from kwik.core.enum import Permissions
from kwik.exceptions import DuplicatedEntity
from kwik.routers import AuditorRouter

router = AuditorRouter()


@router.get(
    "/",
    response_model=schemas.Paginated[schemas.Role],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_roles(paginated: kwik.api.deps.PaginatedQuery) -> kwik.typings.PaginatedResponse[models.Role]:
    """
    Retrieve roles.
    """

    count, roles = crud.role.get_multi(**paginated)
    return kwik.typings.PaginatedResponse(data=roles, total=count)


@router.get(
    "/me",
    response_model=list[schemas.Role],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_role_of_logged_user(current_user: kwik.api.deps.current_user) -> list[models.Role]:
    """
    Get roles of logged-in user.
    """

    return crud.role.get_multi_by_user_id(user_id=current_user.id)


@router.get(
    "/{role_id}/users",
    response_model=schemas.Paginated[schemas.UserORMSchema],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_users_by_role(role_id: int) -> kwik.typings.PaginatedResponse[models.User]:
    """
    Get users by role
    """

    users = crud.role.get_users_by_role_id(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=users, total=len(users))


@router.get(
    "/{role_id}/assignable-users",
    response_model=schemas.Paginated[schemas.UserORMSchema],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_users_not_in_role(role_id: int) -> kwik.typings.PaginatedResponse[models.User]:
    """
    Get all users not involved in the given role
    """

    users = crud.role.get_users_not_in_role(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=users, total=len(users))


@router.get(
    "/{role_id}/permissions",
    response_model=schemas.Paginated[schemas.PermissionORMSchema],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_users_by_role(role_id: int) -> kwik.typings.PaginatedResponse[models.Permission]:
    """
    Get permissions by role
    """

    permissions = crud.role.get_permissions_by_role_id(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=permissions, total=len(permissions))


@router.get(
    "/{role_id}/assignable-permissions",
    response_model=schemas.Paginated[schemas.PermissionORMSchema],
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_permissions_not_assigned_to_role(role_id: int) -> kwik.typings.PaginatedResponse[models.Permission]:
    """
    Get all permissions not assigned to the given role
    """

    permissions = crud.role.get_permissions_not_assigned_to_role(role_id=role_id)
    return kwik.typings.PaginatedResponse(data=permissions, total=len(permissions))


@router.get(
    "/{role_id}",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_read),),
)
def read_role_by_id(role_id: int) -> models.Role:
    """
    Get a specific role by id.
    """

    return crud.role.get(id=role_id)


@router.put(
    "/{role_id}",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_update),),
)
def update_role(role_id: int, role_in: schemas.RoleUpdate) -> models.Role:
    """
    Update a role.
    """

    role = crud.role.get_if_exist(id=role_id)
    return crud.role.update(db_obj=role, obj_in=role_in)


@router.post(
    "/associate",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_update),),
)
def associate_user_to_role(user_role_in: schemas.UserRoleCreate) -> models.Role:
    user = crud.user.get_if_exist(id=user_role_in.user_id)
    role = crud.role.get_if_exist(id=user_role_in.role_id)
    return crud.role.associate_user(user_db=user, role_db=role)


@router.post(
    "/purge",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_update),),
)
def purge_role_from_user(user_role_in: schemas.UserRoleRemove) -> models.Role:
    """
    Remove role from user
    """

    user = crud.user.get_if_exist(id=user_role_in.user_id)
    role = crud.role.get_if_exist(id=user_role_in.role_id)
    return crud.role.purge_user(user_db=user, role_db=role)


@router.post(
    "",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_create),),
)
def create_role(role_in: schemas.RoleCreate) -> models.Role:
    """
    Create new role.
    """

    role = crud.role.get_by_name(name=role_in.name)
    if role is not None:
        raise DuplicatedEntity

    return crud.role.create(obj_in=role_in)


@router.delete(
    "/{role_id}",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_delete),),
)
def delete_role(role_id: int) -> models.Role:
    """
    Delete a role.
    """

    crud.role.get_if_exist(id=role_id)
    return crud.role.remove(id=role_id)


@router.delete(
    "/{name}/deprecate",
    response_model=schemas.Role,
    dependencies=(kwik.api.deps.has_permission(Permissions.roles_management_delete),),
)
def deprecate_role_by_name(name: str) -> models.Role:
    """
    Deprecate role. Remove all associated users
    """

    return crud.role.deprecate(name=name)
