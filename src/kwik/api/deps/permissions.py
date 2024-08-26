from __future__ import annotations

import kwik.crud
from fastapi import Depends
from kwik.exceptions import Forbidden


def has_permission(*permissions: str) -> Depends:
    """
    Endpoint dependency to check if the current user has the required permissions.
    Implemented as a decorator to allow passing multiple permissions as arguments.

    Raises:
        Forbidden: if the user does not have the required permissions
    """

    def check_permissions(current_user: kwik.api.deps.current_user) -> None:
        if not kwik.crud.user.has_permissions(user_id=current_user.id, permissions=permissions):
            raise Forbidden

    return Depends(check_permissions)
