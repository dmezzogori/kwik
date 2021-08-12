from typing import Any, List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import kwik
from app.kwik import crud, models, schemas
from app.kwik.exceptions import NotFound

# TODO switch ad autorouter
router = kwik.routers.AuditorRouter()


@router.get("/", response_model=kwik.schemas.Paginated[schemas.Role])
def read_roles(db: Session = kwik.db, paginated=kwik.PaginatedQuery,) -> Any:
    """
    Retrieve roles.
    """
    count, roles = crud.role.get_multi(db=db, **paginated)
    return {"data": roles, "total": count}


@router.get("/me", response_model=List[schemas.Role])
def read_role_of_logged_user(db: Session = kwik.db, current_user: kwik.models.User = kwik.current_user) -> Any:
    """
    Get roles of logged in user.
    """
    roles = crud.role.get_multi_by_user_id(db=db, user_id=current_user.id)
    return roles


@router.get("/{role_id}/assignable-users", response_model=kwik.schemas.Paginated[schemas.User])
def read_users_not_in_role(role_id: int, db: Session = kwik.db):
    """
    Get all users not involved in the given role
    """
    users = crud.role.get_users_not_in_role(db=db, role_id=role_id)
    return {"data": users, "total": len(users)}


@router.get("/{role_id}/permissions", response_model=kwik.schemas.Paginated[schemas.Permission])
def read_users_by_role(*, db: Session = kwik.db, role_id: int,) -> Any:
    """
    Get permissions by role
    """
    permissions = crud.role.get_permissions_by_role_id(db=db, role_id=role_id)
    return {"data": permissions, "total": len(permissions)}


@router.get("/{role_id}/assignable-permissions", response_model=kwik.schemas.Paginated[schemas.Permission])
def read_users_not_in_role(role_id: int, db: Session = kwik.db):
    """
    Get all permissions not involved in the given role
    """
    permissions = crud.role.get_permissions_not_in_role(db=db, role_id=role_id)
    return {"data": permissions, "total": len(permissions)}


@router.get("/{role_id}", response_model=schemas.Role)
def read_role_by_id(role_id: int, db: Session = kwik.db,) -> Any:
    """
    Get a specific role by id.
    """
    role = crud.role.get(db=db, id=role_id)
    return role


@router.post("/", response_model=schemas.Role)
def create_role(
    *, db: Session = kwik.db, role_in: schemas.RoleCreate, current_user: models.User = kwik.current_user
) -> Any:
    """
    Create new role.
    """
    role = crud.role.get_by_name(db=db, name=role_in.name)
    if role:
        raise HTTPException(
            status_code=400, detail="The role with this name already exists in the system.",
        )
    role = crud.role.create(db=db, obj_in=role_in, user=current_user)
    return role


@router.put("/{role_id}", response_model=schemas.Role)
def update_role(*, db: Session = kwik.db, role_id: int, role_in: schemas.RoleUpdate,) -> Any:
    """
    Update a role.
    """
    role = crud.role.get(db, id=role_id)
    if not role:
        raise NotFound(entity="Role", id=role_id)
    role = crud.role.update(db, db_obj=role, obj_in=role_in)
    return role


@router.delete("/{role_id}", response_model=schemas.Role)
def delete_role(*, db: Session = kwik.db, role_id: int,) -> Any:
    """
    Delete a role.
    """
    role = crud.role.get(db=db, id=role_id)
    if not role:
        raise NotFound(entity="Role", id=role_id)
    role = crud.role.remove(db=db, id=role_id)
    return role


@router.post("/associate", response_model=schemas.Role)
def associate_user_to_role(*, db: Session = kwik.db, current_user = kwik.current_user, user_role_in: schemas.UserRoleCreate) -> Any:
    user = crud.user.get(db=db, id=user_role_in.user_id)
    if not user:
        raise NotFound(entity="User", id=user_role_in.user_id)
    role = crud.role.get(db=db, id=user_role_in.role_id)
    if not role:
        raise NotFound(entity="Role", id=user_role_in.role_id)
    role = crud.role.associate_user(db=db, user_db=user, role_db=role, creator_user=current_user)
    return role


@router.get("/{name}/users", response_model=List[schemas.User])
def read_users_by_role(*, db: Session = kwik.db, name: str,) -> Any:
    """
    Get users by role
    """
    users = crud.role.get_users_by_name(db=db, name=name)
    return users


@router.delete("/{name}/deprecate", response_model=schemas.Role)
def deprecate_role_by_name(*, db: Session = kwik.db, name: str,) -> Any:
    """
    Deprecate role. Remove all associated users
    """
    role = crud.role.deprecate(db=db, name=name)
    return role


@router.post("/", response_model=schemas.Role)
def purge_role_from_user(*, db: Session = kwik.db, user_role_in: schemas.UserRoleRemove) -> Any:
    """
    Remove role from user
    """
    user = crud.user.get(db=db, id=user_role_in.user_id)
    if not user:
        raise NotFound(entity="User", id=user_role_in.user_id)
    role = crud.role.get(db=db, id=user_role_in.role_id)
    if not role:
        raise NotFound(entity="Role", id=user_role_in.role_id)
    role = crud.role.purge_user(db=db, user_db=user, role_db=role)
    return role
