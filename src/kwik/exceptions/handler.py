"""Exception handlers for FastAPI error responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import Request

    from kwik.exceptions import KwikException


async def kwik_exception_handler(request: Request, exc: KwikException) -> JSONResponse:
    """Handle KwikException by returning JSON response with error details."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
