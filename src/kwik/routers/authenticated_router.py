"""Audit router for HTTP request logging."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kwik.api.deps.token import get_token


# TODO: controllare documentazione
class AuthenticatedRouter(APIRouter):
    """
    Router with built-in audit logging for all registered routes.

    This router automatically applies audit logging to all routes registered with it.
    It extends FastAPI's APIRouter to provide comprehensive request/response tracking
    including user context, timing, and request details.

    Features:
    - Automatic JWT token validation for all routes via get_token dependency
    - Request/response audit logging through AuditedRoute class
    - User context management with impersonation support
    - Response time tracking with X-Response-Time header
    - Request body caching for multiple reads
    - Integration with Kwik's audit system for compliance and monitoring

    The router uses AuditedRoute which logs:
    - Client information (host, headers)
    - Request details (method, URL, query params, path params, body)
    - User context (user ID, impersonator ID if applicable)
    - Response information (status code, processing time)
    - Unique request ID for tracing

    All audit records are stored using the crud.audit.create() method.
    """

    def __init__(self, prefix: str) -> None:
        """
        Initialize auditor router with token dependency and audited route class.

        Sets up the router with:
        - get_token dependency applied to all routes for JWT validation
        - _AuditedRoute as the route class for automatic audit logging
        """
        super().__init__(
            prefix=prefix,
            tags=[prefix.strip("/")],
            dependencies=[Depends(get_token)],
        )


__all__ = ["AuthenticatedRouter"]
