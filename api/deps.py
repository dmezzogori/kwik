from typing import Any, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

import kwik
from kwik import crud, models
from kwik.core import security
from kwik.core.enum import PermissionNamesBase
from kwik.db.session import get_db_from_request

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{kwik.settings.API_V1_STR}/login/access-token")

db = Depends(get_db_from_request)


def _get_current_user(db: Session = db, token: str = Depends(reusable_oauth2)) -> models.User:
    try:
        token_data = security.decode_token(token)
    except (jwt.JWTError, ValidationError):
        raise kwik.exceptions.Forbidden()

    user = crud.user.get(db=db, id=token_data.sub)
    if user is None:
        raise kwik.exceptions.Forbidden()

    return user


current_user = Depends(_get_current_user)


def _get_current_active_user(current_user: models.User = current_user) -> models.User:
    if not crud.user.is_active(current_user):
        raise kwik.exceptions.UserInactive()
    return current_user


current_active_user = Depends(_get_current_active_user)


def _get_current_active_superuser(current_user: models.User = current_user) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise kwik.exceptions.Forbidden(detail="The user doesn't have enough privileges")
    return current_user


current_active_superuser = Depends(_get_current_active_superuser)


def has_permission(*permissions: PermissionNamesBase):
    def inner(db: Session = db, current_user: models.User = current_user):
        r = (
            db.query(models.Permission)
            .join(models.RolePermission, models.Role, models.UserRole)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(models.Permission.name.in_([p.value for p in permissions]), models.User.id == current_user.id,)
            .count()
        )
        if r == 0:
            raise kwik.exceptions.Forbidden(detail="The user doesn't have enough privileges")

    return Depends(inner)


def _sorting_query(sorting: Optional[kwik.typings.SortingQuery] = None,) -> kwik.typings.ParsedSortingQuery:
    if sorting is not None:
        sort = []
        for elem in sorting.split(","):
            if ":" in elem:
                attr, order = elem.split(":")
            else:
                attr = elem
                order = "asc"
            sort.append((attr, order))

        return sort


SortingQuery = Depends(_sorting_query)


def _filters(filter: Optional[str] = None, value: Optional[Any] = None):
    filter_d = {}
    if filter and value:
        filter_d = {filter: value}
    return filter_d


FilterQuery = Depends(_filters)


def _paginated(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}


PaginatedQuery = Depends(_paginated)
