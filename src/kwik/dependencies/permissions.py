"""Permission checking dependencies for FastAPI endpoints."""

from __future__ import annotations

from fastapi import Depends

from kwik.crud import crud_users
from kwik.exceptions import AccessDeniedError

from .users import current_user  # noqa: TC001


def has_permission(*permissions: str) -> Depends:
    """
    Endpoint dependency to check if the current user has the required permissions.

    Implemented as a decorator to allow passing multiple permissions as arguments.

    Raises:
        Forbidden: if the user does not have the required permissions

    """

    def check_permissions(user: current_user) -> None:
        if not crud_users.has_permissions(user=user, permissions=permissions):
            raise AccessDeniedError

    return Depends(check_permissions)


__all__ = ["has_permission"]
