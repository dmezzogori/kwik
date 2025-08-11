"""Kwik FastAPI application factory and configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import kwik.exceptions.handler
import kwik.logger
from kwik.core.settings import get_settings
from kwik.exceptions import KwikError

if TYPE_CHECKING:
    from fastapi import APIRouter


class Kwik:
    """
    Kwik Application is a thin and opinionated wrapper around FastAPI.

    It instantiates the FastAPI application and adds some middlewares (CORS,
    RequestContextMiddleware, DBSessionMiddleware).
    It automatically registers all the endpoints from the api_router.
    It also patches the FastAPI docs endpoint to have collapsable sections in the swagger UI.
    """

    def __init__(self, api_router: APIRouter) -> None:
        """Initialize Kwik application with API router."""
        self._app = self._init_fastapi_app(api_router=api_router)

        kwik.logger.info(
            f"Kwik App running on {get_settings().PROTOCOL}://{get_settings().BACKEND_HOST}:{get_settings().BACKEND_PORT}",
        )
        kwik.logger.info(
            f"Swagger available at {get_settings().PROTOCOL}://{get_settings().BACKEND_HOST}:{get_settings().BACKEND_PORT}/docs",
        )

    @property
    def app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self._app

    def _init_fastapi_app(self, *, api_router: APIRouter) -> FastAPI:
        """
        Initialize the FastAPI application.

        Based on the settings, it will also add the websockets on_startup and on_shutdown events.
        Register the api_router.
        Register the KwikException handler.
        Customize the swagger UI.
        """
        app = FastAPI(
            title=get_settings().PROJECT_NAME,
            openapi_url=f"{get_settings().API_V1_STR}/openapi.json",
            debug=get_settings().DEBUG,
            redirect_slashes=False,
        )

        app.add_middleware(ProxyHeadersMiddleware)
        app.add_middleware(GZipMiddleware)

        if get_settings().BACKEND_CORS_ORIGINS:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=tuple(str(origin) for origin in get_settings().BACKEND_CORS_ORIGINS),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["content-disposition"],
            )

        app.include_router(api_router, prefix=get_settings().API_V1_STR)

        app.exception_handler(KwikError)(kwik.exceptions.handler.kwik_exception_handler)

        return app
