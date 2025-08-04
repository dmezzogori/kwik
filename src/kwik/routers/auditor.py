"""Audit router for HTTP request logging."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request, Response
from fastapi.routing import APIRoute
from jose import jwt

from kwik import crud, schemas
from kwik.api.deps.token import get_token
from kwik.api.deps.users import get_current_user
from kwik.core import security
from kwik.core.settings import get_settings
from kwik.database.context_vars import current_user_ctx_var
from kwik.middlewares import get_request_id

if TYPE_CHECKING:
    from collections.abc import Callable


class _KwikRequest(Request):
    """Extended Request class with body caching and token extraction support."""

    async def body(self) -> bytes:
        """Cache request body for multiple reads."""
        if not hasattr(self, "_body"):
            body = await super().body()
            self._body = body
        return self._body

    @property
    def token(self) -> str | None:
        """Extract JWT token from Authorization header."""
        auth = self.headers.get("Authorization")
        if auth is not None and "Bearer " in auth:
            return auth.replace("Bearer ", "")
        return None


class _AuditedRoute(APIRoute):
    """API route with automatic audit logging and user context management."""

    def get_route_handler(self) -> Callable:
        """Create route handler with audit logging support."""
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # start the timer
            start = time.time()

            # override the request object
            request = _KwikRequest(request.scope, request.receive)
            body = await request.body()

            # we set the current user in the context variable
            user_ctx_token = None
            user_id = None
            impersonator_user_id = None
            if request.token is not None:
                user = get_current_user(token=get_token(request.token))
                user_ctx_token = current_user_ctx_var.set(user)
                user_id = user.id

                payload = jwt.decode(
                    request.token,
                    get_settings().SECRET_KEY,
                    algorithms=[security.ALGORITHM],
                )
                token_data = schemas.TokenPayload(**payload)

                if token_data.kwik_impersonate != "":
                    impersonator_user_id = int(token_data.kwik_impersonate)

            # let's process the request
            response: Response = await original_route_handler(request)

            # as soon as the response is ready, we can reset the user context variable
            if user_ctx_token is not None:
                current_user_ctx_var.reset(user_ctx_token)

            # we stop the timer
            process_time = time.time() - start
            response.headers["X-Response-Time"] = str(process_time)

            # let's audit the request
            audit_in = schemas.AuditCreateSchema(
                client_host=request.client.host,
                request_id=get_request_id(),
                user_id=user_id,
                impersonator_user_id=impersonator_user_id,
                method=request.method,
                headers=repr(request.headers),
                url=request.url.path,
                query_params=repr(request.query_params),
                path_params=repr(request.path_params),
                body=str(body),
                process_time=process_time * 1_000,
                status_code=response.status_code,
            )
            crud.audit.create(obj_in=audit_in)
            return response

        return custom_route_handler


class AuditorRouter(APIRouter):
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
            prefix=prefix, tags=[prefix.strip("/")], dependencies=[Depends(get_token)], route_class=_AuditedRoute,
        )


__all__ = ["AuditorRouter"]
