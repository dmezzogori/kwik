"""Database session middleware for request lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from kwik.database.db_context_manager import DBContextManager

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response


class DBSessionMiddleware(BaseHTTPMiddleware):
    """Middleware providing database session management for HTTP requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle request within database session context manager."""
        with DBContextManager():
            return await call_next(request)
