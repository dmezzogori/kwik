"""API routers package for kwik framework."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kwik.dependencies.api_key import verify_api_key
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


class ApiKeyRouter(APIRouter):
    """
    Router that authenticates requests via API key.

    Injects ``verify_api_key`` as a router-level dependency, requiring
    every endpoint on this router to present a valid ``X-API-Key`` header.
    Structurally identical to ``AuthenticatedRouter`` but uses API key
    validation instead of JWT bearer token validation.

    The resolved user is stored on ``request.state.api_key_user``, which
    allows shared dependencies like ``has_permission`` to work
    transparently on both router types.

    Args:
        prefix: URL prefix for all routes on this router.

    """

    def __init__(self, prefix: str) -> None:
        """Initialize router with mandatory API key authentication."""
        super().__init__(
            prefix=prefix,
            tags=[prefix.strip("/")],
            dependencies=[Depends(verify_api_key)],
        )


__all__ = ["ApiKeyRouter", "AuthenticatedRouter"]
