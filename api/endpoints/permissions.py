from typing import Any, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.kwik import crud, schemas
from app import kwik
from app import models


router = kwik.routers.AuditorRouter()


@router.get("/", response_model=List[schemas.Permission])
def read_permissions(db: Session = kwik.db, skip: int = 0, limit: int = 100,) -> Any:
    """
    Retrieve permissions.
    """
    # TODO total count
    _, permissions = crud.permission.get_multi(db, skip=skip, limit=limit)
    return permissions


@router.post("/", response_model=schemas.Permission)
def create_permission(
    *, db: Session = kwik.db, permission_in: schemas.PermissionCreate, current_user: models.User = kwik.current_user
) -> Any:
    """
    Create new permission.
    """
    permission = crud.permission.get_by_name(db, name=permission_in.name)
    if permission:
        raise HTTPException(
            status_code=400, detail="The permission with this name already exists in the system.",
        )
    permission = crud.permission.create(db, obj_in=permission_in, user=current_user)
    return permission


@router.post("/associate", response_model=schemas.Permission)
def associate_permission_to_role(*, db: Session = kwik.db, permission_role_in: schemas.PermissionRoleCreate) -> Any:
    permission = crud.permission.get(db=db, id=permission_role_in.permission_id)
    if not permission:
        raise HTTPException(
            status_code=412, detail="The specified permission does not exists in the system.",
        )
    role = crud.role.get(db=db, id=permission_role_in.role_id)
    if not role:
        raise HTTPException(
            status_code=412, detail="The specified role does not exists in the system.",
        )
    permission = crud.permission.associate_role(db=db, permission_db=permission, role_db=role)
    return permission


@router.get("/{permission_id}", response_model=schemas.Permission)
def read_permission_by_id(permission_id: int, db: Session = kwik.db,) -> Any:
    """
    Get a specific permission by id.
    """
    permission = crud.permission.get(db, id=permission_id)
    return permission


@router.put("/{permission_id}", response_model=schemas.Permission)
def update_permission(*, db: Session = kwik.db, permission_id: int, permission_in: schemas.PermissionUpdate,) -> Any:
    """
    Update a permission.
    """
    permission = crud.permission.get(db, id=permission_id)
    if not permission:
        raise HTTPException(
            status_code=404, detail="The permission with this id does not exist in the system",
        )
    permission = crud.permission.update(db, db_obj=permission, obj_in=permission_in)
    return permission


@router.delete("/{name}/deprecate", response_model=schemas.Permission)
def deprecate_permission_by_name(*, db: Session = kwik.db, name: str,) -> Any:
    """
    Deprecate permission. Remove all associated roles
    """
    permission = crud.permission.deprecate(db=db, name=name)
    return permission


@router.delete("/{permission_id}", response_model=schemas.Permission)
def delete_permission(*, db: Session = kwik.db, permission_id: int,) -> Any:
    """
    Delete a role.
    """
    permission = crud.permission.get(db=db, id=permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    permission = crud.permission.remove(db=db, id=permission_id)
    return permission


@router.delete("/", response_model=schemas.Permission)
def purge_role_from_permission(*, db: Session = kwik.db, permission_role_in: schemas.PermissionRoleRemove) -> Any:
    """
    Remove permission from role
    """
    permission = crud.permission.get(db=db, id=permission_role_in.permission_id)
    if not permission:
        raise HTTPException(
            status_code=412, detail="The specified permission does not exists in the system.",
        )
    role = crud.role.get(db=db, id=permission_role_in.role_id)
    if not role:
        raise HTTPException(
            status_code=412, detail="The specified role does not exists in the system.",
        )
    permission = crud.permission.purge_role(db=db, permission_db=permission, role_db=role)
    return permission
