from typing import Any, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError

from kwik import crud
from kwik.core import security
from kwik.core.enum import PermissionNamesBase
from kwik.database.session import KwikSession, get_db_from_request
from kwik.exceptions import Forbidden, UserInactive
from kwik.models import User, Permission, RolePermission, Role, UserRole
from kwik.typings import ParsedSortingQuery, SortingQuery

from kwik.db.session import get_db_from_request

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{kwik.settings.API_V1_STR}/login/access-token")

db = Depends(get_db_from_request)


def get_current_user(
    db: KwikSession = db, token: str = Depends(reusable_oauth2)
) -> User:
    try:
        token_data = security.decode_token(token)
    except (jwt.JWTError, ValidationError):
        raise Forbidden()

    user = crud.user.get(db=db, id=token_data.sub)
    if user is None:
        raise Forbidden()

    return user


current_user = Depends(get_current_user)


def get_current_active_user(current_user: User = current_user) -> User:
    if not crud.user.is_active(current_user):
        raise UserInactive()
    return current_user


current_active_user = Depends(get_current_active_user)


def get_current_active_superuser(current_user: User = current_user) -> User:
    if not crud.user.is_superuser(current_user):
        raise Forbidden(detail="The user doesn't have enough privileges")
    return current_user


current_active_superuser = Depends(_get_current_active_superuser)


def has_permission(*permissions: PermissionNamesBase):
    def inner(db: KwikSession = db, current_user: User = current_user):
        r = (
            db.query(Permission)
            .join(RolePermission, Role, UserRole)
            .join(User, User.id == UserRole.user_id)
            .filter(
                Permission.name.in_([p.value for p in permissions]),
                User.id == current_user.id,
            )
            .count()
        )
        if r == 0:
            raise Forbidden(detail="The user doesn't have enough privileges")

    return Depends(inner)


def sorting_query(sorting: Optional[SortingQuery] = None,) -> ParsedSortingQuery:
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


FilterQuery = Depends(_filters)


def _paginated(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}


PaginatedQuery = Depends(_paginated)
