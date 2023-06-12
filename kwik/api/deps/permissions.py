from __future__ import annotations

import kwik.crud
from fastapi import Depends


def has_permission(*permissions: str) -> Depends:
    """
    Endpoint dependency to check if the current user has the required permissions.
    Implemented as a decorator to allow passing multiple permissions as arguments.

    Raises:
        Forbidden: if the user does not have the required permissions
    """

    def check_permissions() -> None:
        kwik.crud.user.has_permissions(permissions=permissions)

    return Depends(check_permissions)
