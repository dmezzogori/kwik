"""Database session middleware for request lifecycle."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from kwik.database.db_context_manager import DBContextManager


class DBSessionMiddleware(BaseHTTPMiddleware):
    """Middleware providing database session management for HTTP requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Handle request within database session context manager."""
        with DBContextManager():
            response = await call_next(request)

        return response
