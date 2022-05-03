from __future__ import annotations

from fastapi import FastAPI, APIRouter
from kwik import settings
from kwik.api.endpoints.docs import get_swagger_ui_html
from kwik.middlewares import RequestContextMiddleware, DBSessionMiddleware
from kwik.websocket.deps import broadcast
from starlette.middleware.cors import CORSMiddleware
import kwik


def set_running_app(app: FastAPI):
    kwik._running_app = app


def get_running_app() -> FastAPI | None:
    return kwik._running_app


def run(kwik_app: str | Kwik):
    import uvicorn

    reload = settings.HOTRELOAD
    if isinstance(kwik_app, str):
        kwik_app = f"{kwik_app}._app"
    else:
        reload = False

    uvicorn.run(
        kwik_app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=reload,
        http="httptools",
        ws="websockets",
        proxy_headers=True,
    )


class Kwik:
    """
    Kwik Application is a thin and opinionated wrapper around FastAPI.
    It instantiates the FastAPI application and adds some middlewares (CORS,
    RequestContextMiddleware, DBSessionMiddleware).
    It automatically registers all the endpoints from the api_router.
    It also patches the FastAPI docs endpoint to have collapsable sections in the swagger UI.
    """

    def __init__(self, api_router: APIRouter):
        on_startup = []
        on_shutdown = []
        if settings.WEBSOCKET_ENABLED:
            on_startup = [broadcast.connect]
            on_shutdown = [broadcast.disconnect]

        self._app = FastAPI(
            title=settings.PROJECT_NAME,
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            debug=settings.DEBUG,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            docs_url=None,
        )

        self._app.add_middleware(RequestContextMiddleware)
        self._app.add_middleware(DBSessionMiddleware)

        if settings.BACKEND_CORS_ORIGINS:
            self._app.add_middleware(
                CORSMiddleware,
                allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["content-disposition"],
            )

        self._app.include_router(api_router, prefix=settings.API_V1_STR)

        @self._app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(openapi_url=self._app.openapi_url, title=self._app.title + " - Swagger UI")

        set_running_app(self._app)

        from kwik import logger

        logger.info("Kwik App instantiated")
