"""Exception handlers for FastAPI error responses."""

from __future__ import annotations

from fastapi import Request
from starlette.responses import JSONResponse

from kwik.exceptions import KwikException


async def kwik_exception_handler(request: Request, exc: KwikException):
    """Handle KwikException by returning JSON response with error details."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
