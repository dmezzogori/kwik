from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from kwik import api_router
from kwik import settings
from kwik.api.endpoints.docs import get_swagger_ui_html
from kwik.middlewares import RequestContextMiddleware, DBSessionMiddleware
from kwik.websocket.deps import broadcast


class Kwik:
    def __init__(self):

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

        from kwik import logger

        logger.info("Kwik App instantiated")
