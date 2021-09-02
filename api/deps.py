from typing import Any, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import kwik
from app.kwik import crud, models
from app.kwik.core import security
from app.kwik.core.config import settings
from app.kwik.core.enum import PermissionNamesBase
from app.kwik.db.session import get_db_from_request

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")

db = Depends(get_db_from_request)


def get_current_user(db: Session = db, token: str = Depends(reusable_oauth2)) -> models.User:
    try:
        token_data = security.decode_token(token)
    except (jwt.JWTError, ValidationError):
        raise kwik.exceptions.Forbidden()

    user = crud.user.get(db=db, id=token_data.sub)
    if user is None:
        raise kwik.exceptions.Forbidden()

    return user


current_user = Depends(get_current_user)


def get_current_active_user(current_user: models.User = current_user,) -> models.User:
    if not crud.user.is_active(current_user):
        raise kwik.exceptions.UserInactive()
    return current_user


current_active_user = Depends(get_current_active_user)


def get_current_active_superuser(current_user: models.User = current_user,) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise kwik.exceptions.Forbidden(detail="The user doesn't have enough privileges")
    return current_user


current_active_superuser = Depends(get_current_active_superuser)


def has_permission(*permissions: PermissionNamesBase):
    def inner(db: Session = db, current_user: models.User = current_user):
        r = (
            db.query(models.Permission)
            .join(models.RolePermission, models.Role, models.UserRole)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(models.Permission.name.in_([p.value for p in permissions]), models.User.id == current_user.id,)
            .one_or_none()
        )
        if r is None:
            raise kwik.exceptions.Forbidden(detail="The user doesn't have enough privileges")

    return Depends(inner)


def sorting_query(sorting: Optional[kwik.typings.SortingQuery] = None) -> kwik.typings.ParsedSortingQuery:
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


SortingQuery = Depends(sorting_query)


def filters(filter: Optional[str] = None, value: Optional[Any] = None):
    filter_d = {}
    if filter and value:
        filter_d = {filter: value}
    return filter_d


FilterQuery = Depends(filters)


def paginated(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}


PaginatedQuery = Depends(paginated)
