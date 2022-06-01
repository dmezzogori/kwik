from typing import Any, Callable

import kwik
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from kwik import crud
from kwik.core import security
from kwik.core.enum import PermissionNamesBase
from kwik.database.session import KwikSession, get_db_from_request
from kwik.exceptions import Forbidden
from kwik.models import User, Permission, RolePermission, Role, UserRole
from kwik.typings import ParsedSortingQuery, SortingQuery
from pydantic import ValidationError

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{kwik.settings.API_V1_STR}/login/access-token")

db = Depends(get_db_from_request)


# noinspection PyShadowingNames
def get_current_user(db: KwikSession = db, token: str = Depends(reusable_oauth2)) -> User:
    try:
        token_data = security.decode_token(token)
    except (jwt.JWTError, ValidationError):
        raise Forbidden().http_exc

    user = crud.user.get(db=db, id=token_data.sub)
    if user is None:
        raise Forbidden().http_exc

    return user


current_user = Depends(get_current_user)


def has_permission(*permissions: PermissionNamesBase) -> Callable:
    # noinspection PyShadowingNames
    def inner(db: KwikSession = db, user: User = current_user) -> None:
        r = (
            db.query(Permission)
            .join(RolePermission, Role, UserRole)
            .join(User, User.id == UserRole.user_id)
            .filter(
                Permission.name.in_([p.value for p in permissions]),
                User.id == user.id,
            )
            .count()
        )
        if r == 0:
            raise Forbidden().http_exc

    return Depends(inner)


def sorting_query(
    sorting: SortingQuery | None = None,
) -> ParsedSortingQuery:
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


# noinspection PyShadowingBuiltins
def _filters(filter: str | None = None, value: Any | None = None):
    filter_d = {}
    if filter and value:
        filter_d = {filter: value}
    return filter_d


FilterQuery = Depends(_filters)


def _paginated(skip: int = 0, limit: int = 100):
    return {"skip": skip, "limit": limit}


PaginatedQuery = Depends(_paginated)
