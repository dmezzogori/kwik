from typing import Any, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.kwik import crud, schemas
from app import kwik


router = kwik.routers.AuditorRouter()


@router.get("/", response_model=List[schemas.Role])
def read_roles(
    db: Session = kwik.db,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve roles.
    """
    # TODO total count
    _, roles = crud.role.get_multi(db, skip=skip, limit=limit)
    return roles


@router.post("/", response_model=schemas.Role)
def create_role(
    *,
    db: Session = kwik.db,
    role_in: schemas.RoleCreate,
) -> Any:
    """
    Create new role.
    """
    role = crud.role.get_by_name(db, name=role_in.name)
    if role:
        raise HTTPException(
            status_code=400,
            detail="The role with this name already exists in the system.",
        )
    role = crud.role.create(db, obj_in=role_in)
    return role


@router.post("/associate", response_model=schemas.Role)
def associate_user_to_role(
    *,
    db: Session = kwik.db,
    user_role_in: schemas.UserRoleCreate
) -> Any:
    user = crud.user.get(db=db, id=user_role_in.user_id)
    if not user:
        raise HTTPException(
            status_code=412,
            detail="The specified user does not exists in the system.",
        )
    role = crud.role.get(db=db, id=user_role_in.role_id)
    if not role:
        raise HTTPException(
            status_code=412,
            detail="The specified role does not exists in the system.",
        )
    role = crud.role.associate_user(db=db, user_db=user, role_db=role)
    return role


@router.get("/me", response_model=List[schemas.Role])
def read_role_of_logged_user(
    db: Session = kwik.db,
    current_user: kwik.models.User = kwik.current_user
) -> Any:
    """
    Get roles of logged in user.
    """
    roles = crud.role.get_multi_by_user_id(db, user_id=current_user.id)
    return roles


@router.get("/{role_id}", response_model=schemas.Role)
def read_role_by_id(
    role_id: int,
    db: Session = kwik.db,
) -> Any:
    """
    Get a specific role by id.
    """
    role = crud.role.get(db, id=role_id)
    return role


@router.get("/{name}/users", response_model=List[schemas.User])
def read_users_by_role(
    *,
    db: Session = kwik.db,
    name: str,
) -> Any:
    """
    Get users by role
    """
    users = crud.role.get_users_by_name(db=db, name=name)
    return users


@router.put("/{role_id}", response_model=schemas.Role)
def update_role(
    *,
    db: Session = kwik.db,
    role_id: int,
    role_in: schemas.RoleUpdate,
) -> Any:
    """
    Update a role.
    """
    role = crud.role.get(db, id=role_id)
    if not role:
        raise HTTPException(
            status_code=404,
            detail="The role with this id does not exist in the system",
        )
    role = crud.role.update(db, db_obj=role, obj_in=role_in)
    return role


@router.delete("/{name}/deprecate", response_model=schemas.Role)
def deprecate_role_by_name(
    *,
    db: Session = kwik.db,
    name: str,
) -> Any:
    """
    Deprecate role. Remove all associated users
    """
    role = crud.role.deprecate(db=db, name=name)
    return role


@router.delete("/{role_id}", response_model=schemas.Role)
def delete_role(
    *,
    db: Session = kwik.db,
    role_id: int,
) -> Any:
    """
    Delete a role.
    """
    role = crud.role.get(db=db, id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role = crud.role.remove(db=db, id=role_id)
    return role


@router.delete("/", response_model=schemas.Role)
def purge_role_from_user(
    *,
    db: Session = kwik.db,
    user_role_in: schemas.UserRoleRemove
) -> Any:
    """
    Remove role from user
    """
    user = crud.user.get(db=db, id=user_role_in.user_id)
    if not user:
        raise HTTPException(
            status_code=412,
            detail="The specified user does not exists in the system.",
        )
    role = crud.role.get(db=db, id=user_role_in.role_id)
    if not role:
        raise HTTPException(
            status_code=412,
            detail="The specified role does not exists in the system.",
        )
    role = crud.role.purge_user(db=db, user_db=user, role_db=role)
    return role
