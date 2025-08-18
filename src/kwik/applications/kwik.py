"""Kwik FastAPI application factory and configuration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pprint import pformat
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from kwik.database import create_engine, create_session_factory, session_scope
from kwik.exceptions import KwikError, kwik_exception_handler, value_error_handler
from kwik.logging import logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable
    from contextlib import AbstractAsyncContextManager

    from fastapi import APIRouter
    from sqlalchemy.orm import Session

    from kwik.settings import BaseKwikSettings


def _make_lifespan(
    settings: BaseKwikSettings,
    seed_db: Callable[[Session, BaseKwikSettings], None] | None = None,
) -> Callable[[FastAPI], AbstractAsyncContextManager]:
    """
    Create a lifespan context manager for FastAPI application.

    This function creates and returns an async context manager that handles
    the application startup and shutdown lifecycle. During startup, it
    initializes the database engine and session factory, storing them in
    the app state. It also seeds the database if a seeding callable is provided.
    During shutdown, it cleans up resources and disposes
    of the database engine.

    Parameters
    ----------
    settings : BaseKwikSettings
        Application settings containing database configuration and environment details.
    seed_db : Callable[[Session], None]
        Function to seed the database.

    Returns
    -------
    Callable[[FastAPI], AbstractAsyncContextManager]
        An async context manager function that can be used as FastAPI's lifespan parameter.

    """

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        _engine = create_engine(settings=settings)
        _session_local = create_session_factory(engine=_engine)

        if seed_db is not None:
            with session_scope(session=_session_local(), commit=True) as _session:
                seed_db(_session, settings)

        # Store in app state for middleware access
        app.state.settings = settings
        app.state.SessionLocal = _session_local

        try:
            logger.debug("Kwik application lifespan started.")
            logger.debug(f"Initializing Kwik application with settings: {pformat(settings.model_dump())}")
            yield
        finally:
            # Clean up app state
            delattr(app.state, "settings")
            delattr(app.state, "SessionLocal")

            _engine.dispose()

            logger.debug("Kwik application lifespan ended.")

    return _lifespan


class Kwik:
    """
    Kwik Application is a thin and opinionated wrapper around FastAPI.

    It instantiates the FastAPI application and adds some middlewares.
    It automatically registers all the endpoints from the api_router.
    """

    def __init__(
        self,
        *,
        settings: BaseKwikSettings,
        api_router: APIRouter,
        seed_db: Callable[[Session, BaseKwikSettings], None] | None = None,
    ) -> None:
        """Initialize Kwik application with API router."""
        self.settings = settings
        self._seed_db = seed_db
        self._app = self._init_fastapi_app(api_router=api_router)

        logger.info(
            f"Kwik App running on {settings.PROTOCOL}://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}",
        )
        logger.info(
            f"Swagger available at {self.settings.PROTOCOL}://{self.settings.BACKEND_HOST}:{self.settings.BACKEND_PORT}/docs",
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
            title=self.settings.PROJECT_NAME,
            openapi_url=f"{self.settings.API_V1_STR}/openapi.json",
            debug=self.settings.DEBUG,
            redirect_slashes=False,
            lifespan=_make_lifespan(self.settings, self._seed_db),
        )

        app.add_middleware(ProxyHeadersMiddleware)
        app.add_middleware(GZipMiddleware)

        if self.settings.BACKEND_CORS_ORIGINS:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=tuple(str(origin) for origin in self.settings.BACKEND_CORS_ORIGINS),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["content-disposition"],
            )

        app.include_router(api_router, prefix=self.settings.API_V1_STR)

        app.exception_handler(KwikError)(kwik_exception_handler)
        app.exception_handler(ValueError)(value_error_handler)

        return app


__all__ = ["Kwik"]
