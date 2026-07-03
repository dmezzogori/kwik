"""Permission checking dependencies for FastAPI endpoints."""

from __future__ import annotations

from fastapi import Depends

from kwik.exceptions import AccessDeniedError

from .users import resolved_user  # noqa: TC001


def has_permission(*permissions: str) -> Depends:
    """
    Endpoint dependency to check if the current user has the required permissions.

    Works transparently on both ``AuthenticatedRouter`` (JWT) and
    ``ApiKeyRouter`` (API key) endpoints. Uses ``resolved_user`` which
    checks ``request.state.api_key_user`` first, then falls back to JWT.

    Raises:
        AccessDeniedError: if the user does not have the required permissions.

    """

    def check_permissions(user: resolved_user) -> None:
        from kwik.kernel import get_kernel  # noqa: PLC0415 — deferred: kernel imports kwik.dependencies

        if not get_kernel().crud_users.has_permissions(user=user, permissions=permissions):
            raise AccessDeniedError

    return Depends(check_permissions)


__all__ = ["has_permission"]
