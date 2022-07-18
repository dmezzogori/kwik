import kwik
from kwik import crud, models, schemas
from kwik.exceptions import NotFound, DuplicatedEntity
from kwik.routers import AuditorRouter

router = AuditorRouter()


@router.get("/", response_model=schemas.Paginated[schemas.Role])
def read_roles(paginated=kwik.PaginatedQuery) -> dict:
    """
    Retrieve roles.
    """
    count, roles = crud.role.get_multi(**paginated)
    return {"data": roles, "total": count}


@router.get("/me", response_model=list[schemas.Role])
def read_role_of_logged_user(current_user: models.User = kwik.current_user) -> list[models.Role]:
    """
    Get roles of logged in user.
    """
    return crud.role.get_multi_by_user_id(user_id=current_user.id)


@router.get("/{role_id}/users", response_model=schemas.Paginated[schemas.User])
def read_users_by_role(role_id: int) -> dict:
    """
    Get users by role
    """
    users = crud.role.get_users_by_role_id(role_id=role_id)
    return {"data": users, "total": len(users)}


@router.get("/{role_id}/assignable-users", response_model=schemas.Paginated[schemas.User])
def read_users_not_in_role(role_id: int) -> dict:
    """
    Get all users not involved in the given role
    """
    users = crud.role.get_users_not_in_role(role_id=role_id)
    return {"data": users, "total": len(users)}


@router.get("/{role_id}/permissions", response_model=schemas.Paginated[schemas.PermissionORMSchema])
def read_users_by_role(role_id: int) -> dict:
    """
    Get permissions by role
    """
    permissions = crud.role.get_permissions_by_role_id(role_id=role_id)
    return {"data": permissions, "total": len(permissions)}


@router.get("/{role_id}/assignable-permissions", response_model=schemas.Paginated[schemas.PermissionORMSchema])
def read_users_not_in_role(role_id: int) -> dict:
    """
    Get all permissions not involved in the given role
    """
    permissions = crud.role.get_permissions_not_in_role(role_id=role_id)
    return {"data": permissions, "total": len(permissions)}


@router.get("/{role_id}", response_model=schemas.Role)
def read_role_by_id(role_id: int) -> models.Role:
    """
    Get a specific role by id.
    """
    return crud.role.get(id=role_id)


@router.put("/{role_id}", response_model=schemas.Role)
def update_role(role_id: int, role_in: schemas.RoleUpdate) -> models.Role:
    """
    Update a role.
    """
    try:
        role = crud.role.get_if_exist(id=role_id)
        return crud.role.update(db_obj=role, obj_in=role_in)
    except NotFound as e:
        raise e.http_exc


@router.post("/associate", response_model=schemas.Role)
def associate_user_to_role(user_role_in: schemas.UserRoleCreate, current_user=kwik.current_user) -> models.Role:
    try:
        user = crud.user.get_if_exist(id=user_role_in.user_id)
        role = crud.role.get_if_exist(id=user_role_in.role_id)
        role = crud.role.associate_user(user_db=user, role_db=role, creator_user=current_user)
        return role
    except NotFound as e:
        raise e.http_exc


@router.post("/purge", response_model=schemas.Role)
def purge_role_from_user(user_role_in: schemas.UserRoleRemove) -> models.Role:
    """
    Remove role from user
    """
    try:
        user = crud.user.get_if_exist(id=user_role_in.user_id)
        role = crud.role.get_if_exist(id=user_role_in.role_id)
        role = crud.role.purge_user(user_db=user, role_db=role)
        return role
    except NotFound as e:
        raise e.http_exc


@router.post("/", response_model=schemas.Role)
def create_role(
    role_in: schemas.RoleCreate,
) -> models.Role:
    """
    Create new role.
    """
    role = crud.role.get_by_name(name=role_in.name)
    if role is not None:
        raise DuplicatedEntity().http_exc
    return crud.role.create(obj_in=role_in)


@router.delete("/{role_id}", response_model=schemas.Role)
def delete_role(
    role_id: int,
) -> models.Role:
    """
    Delete a role.
    """
    try:
        crud.role.get_if_exist(id=role_id)
        return crud.role.remove(id=role_id)
    except NotFound as e:
        raise e.http_exc


@router.delete("/{name}/deprecate", response_model=schemas.Role)
def deprecate_role_by_name(
    name: str,
) -> models.Role:
    """
    Deprecate role. Remove all associated users
    """
    return crud.role.deprecate(name=name)
