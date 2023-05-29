from __future__ import annotations

from fastapi import Request
from kwik.exceptions import KwikException
from starlette.responses import JSONResponse


async def kwik_exception_handler(request: Request, exc: KwikException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
