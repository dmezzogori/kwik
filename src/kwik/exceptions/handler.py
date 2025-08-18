"""Exception handlers for FastAPI error responses."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import Request

    from kwik.exceptions import KwikError


async def kwik_exception_handler(request: Request, exc: KwikError) -> JSONResponse:  # noqa: ARG001
    """Handle KwikException by returning JSON response with error details."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:  # noqa: ARG001
    """Map validation `ValueError` to a Bad Request JSON response."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})
