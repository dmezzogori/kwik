from __future__ import annotations

from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

import kwik
from kwik import crud
from kwik.core import security
from kwik.core.enum import PermissionNamesBase
from kwik.database.session import get_db_from_request
from kwik.exceptions import Forbidden
from kwik.models import User
from kwik.schemas import TokenPayload
from kwik.typings import ParsedSortingQuery, SortingQuery

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{kwik.settings.API_V1_STR}/login/access-token")

db = Depends(get_db_from_request)


def get_token(token: str = Depends(reusable_oauth2)) -> TokenPayload:
    try:
        return security.decode_token(token)
    except Forbidden as e:
        raise e.http_exc


current_token = Depends(get_token)


def get_current_user(token: TokenPayload = current_token) -> User:
    user = crud.user.get(id=token.sub)
    if user is None:
        raise Forbidden().http_exc
    return user


current_user = Depends(get_current_user)


def has_permission(*permissions: PermissionNamesBase) -> Depends:
    def check_permissions(user: User = current_user) -> None:
        try:
            crud.user.has_permissions(user_id=user.id, permissions=permissions)
        except Forbidden as e:
            raise e.http_exc

    return Depends(check_permissions)


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


SortingQuery: ParsedSortingQuery = Depends(sorting_query)


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
