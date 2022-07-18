from kwik import crud, models, schemas
from kwik.exceptions import NotFound, DuplicatedEntity
from kwik.routers import AuditorRouter

router = AuditorRouter()


@router.get("/", response_model=list[schemas.PermissionORMSchema])
def read_permissions(
    skip: int = 0,
    limit: int = 100,
) -> list[models.Permission]:
    """
    Retrieve permissions.
    """
    _, permissions = crud.permission.get_multi(skip=skip, limit=limit)
    return permissions


@router.post("/", response_model=schemas.PermissionORMSchema)
def create_permission(permission_in: schemas.PermissionCreate) -> models.Permission:
    """
    Create new permission.
    """
    permission = crud.permission.get_by_name(name=permission_in.name)
    if permission is not None:
        raise DuplicatedEntity().http_exc
    permission = crud.permission.create(obj_in=permission_in)
    return permission


@router.post("/associate", response_model=schemas.PermissionORMSchema)
def associate_permission_to_role(permission_role_in: schemas.PermissionRoleCreate) -> models.Permission:
    try:
        permission = crud.permission.get_if_exist(id=permission_role_in.permission_id)
        role = crud.role.get_if_exist(id=permission_role_in.role_id)
        return crud.permission.associate_role(permission_db=permission, role_db=role)
    except NotFound as e:
        raise e.http_exc


@router.get("/{permission_id}", response_model=schemas.PermissionORMSchema)
def read_permission_by_id(
    permission_id: int,
) -> models.Permission:
    """
    Get a specific permission by id.
    """
    return crud.permission.get_if_exist(id=permission_id)


@router.put("/{permission_id}", response_model=schemas.PermissionORMSchema)
def update_permission(
    permission_id: int,
    permission_in: schemas.PermissionUpdate,
) -> models.Permission:
    """
    Update a permission.
    """
    try:
        permission = crud.permission.get_if_exist(id=permission_id)
        return crud.permission.update(db_obj=permission, obj_in=permission_in)
    except NotFound as e:
        raise e.http_exc


@router.delete("/{name}/deprecate", response_model=schemas.PermissionORMSchema)
def deprecate_permission_by_name(
    name: str,
) -> models.Permission:
    """
    Deprecate permission. Remove all associated roles
    """
    return crud.permission.deprecate(name=name)


@router.delete("/{permission_id}", response_model=schemas.PermissionORMSchema)
def delete_permission(
    permission_id: int,
) -> models.Permission:
    """
    Delete a role.
    """
    try:
        crud.permission.get_if_exist(id=permission_id)
        return crud.permission.remove(id=permission_id)
    except NotFound as e:
        raise e.http_exc


@router.delete("/", response_model=schemas.PermissionORMSchema)
def purge_role_from_permission(permission_role_in: schemas.PermissionRoleRemove) -> models.Permission:
    """
    Remove permission from role
    """
    try:
        permission = crud.permission.get_if_exist(id=permission_role_in.permission_id)
        role = crud.role.get_if_exist(id=permission_role_in.role_id)
        return crud.permission.purge_role(permission_db=permission, role_db=role)
    except NotFound as e:
        raise e.http_exc
