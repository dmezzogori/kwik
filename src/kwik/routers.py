"""API routers package for kwik framework."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kwik.dependencies.token import get_token


class AuthenticatedRouter(APIRouter):
    """
    Router that requires JWT authentication for all registered routes.

    This router extends FastAPI's APIRouter to automatically apply JWT token
    validation to all routes registered with it, ensuring that only authenticated
    users can access the endpoints.

    Features:
    - Automatic JWT token validation for all routes via get_token dependency
    - Consistent authentication enforcement across route groups
    - Simplified router setup with built-in security requirements

    The router automatically adds the get_token dependency to all routes,
    which validates JWT tokens and provides decoded token payload to handlers.
    """

    def __init__(self, prefix: str) -> None:
        """Initialize router with mandatory user authentication."""
        super().__init__(
            prefix=prefix,
            tags=[prefix.strip("/")],
            dependencies=[Depends(get_token)],
        )


__all__ = ["AuthenticatedRouter"]
