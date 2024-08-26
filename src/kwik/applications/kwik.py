from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import kwik.exceptions.handler
import kwik.logger
from kwik import settings
from kwik.api.endpoints.docs import get_swagger_ui_html
from kwik.exceptions import KwikException
from kwik.middlewares import DBSessionMiddleware, RequestContextMiddleware
from kwik.websocket.deps import broadcast

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
        self._app = self.init_fastapi_app(api_router=api_router)

        kwik.logger.info("Kwik App ready")
        kwik.logger.info(f"Kwik App running on {settings.PROTOCOL}://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
        kwik.logger.info(
            f"Swagger available at {settings.PROTOCOL}://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs"
        )

    def init_fastapi_app(self, *, api_router: APIRouter) -> FastAPI:
        """
        Initialize the FastAPI application.

        Based on the settings, it will also add the websockets on_startup and on_shutdown events.
        Register the api_router.
        Register the KwikException handler.
        Customize the swagger UI.
        """

        app = FastAPI(
            title=settings.PROJECT_NAME,
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            debug=settings.DEBUG,
            on_startup=[broadcast.connect] if settings.WEBSOCKET_ENABLED else None,
            on_shutdown=[broadcast.disconnect] if settings.WEBSOCKET_ENABLED else None,
            redirect_slashes=False,
        )

        app = self.set_middlewares(app=app)

        app.include_router(api_router, prefix=settings.API_V1_STR)

        app.exception_handler(KwikException)(kwik.exceptions.handler.kwik_exception_handler)

        return app

    def set_middlewares(self, *, app: FastAPI) -> FastAPI:
        """
        Set the middlewares for the FastAPI application.

        Add the GZipMiddleware, RequestContextMiddleware and DBSessionMiddleware.
        If CORS is enabled, add the CORSMiddleware.
        """

        app.add_middleware(ProxyHeadersMiddleware)
        app.add_middleware(GZipMiddleware)
        app.add_middleware(RequestContextMiddleware)
        app.add_middleware(DBSessionMiddleware)

        if settings.BACKEND_CORS_ORIGINS:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=tuple(str(origin) for origin in settings.BACKEND_CORS_ORIGINS),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["content-disposition"],
            )
        return app

    def customize_swagger_ui(self, *, app: FastAPI) -> FastAPI:
        """
        Customize the swagger UI to have collapsable sections.
        """

        @app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url=app.openapi_url,
                title=app.title + " - Swagger UI",
            )

        return app
