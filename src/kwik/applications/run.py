"""
Kwik application runner with intelligent server selection.

This module provides the main `run()` function that automatically selects and configures
the appropriate ASGI server based on the environment and application type:

Server Selection Logic:
- **Development (APP_ENV="development")**: Uses Uvicorn with hot-reload capabilities,
  optimized HTTP tools, and WebSocket support for fast development iteration.

- **Production (APP_ENV="production")**: Uses Gunicorn with custom Uvicorn workers
  for better process management, load handling, and stability in production environments.

Input Types:
- **String module path**: For running external applications (e.g., "myapp.main")
  - The module must contain an instance of the Kwik app
  - Hot-reload is automatically enabled in development mode

- **Kwik application instance**: For running pre-configured Kwik applications
  - Hot-reload is disabled (application is already instantiated)
  - Direct FastAPI app access through the .app attribute

Configuration:
- Server settings are loaded from BaseKwikSettings via get_settings()
- Production server uses KwikUvicornWorker for optimized performance
- Development server uses direct uvicorn.run() for simplicity and debugging
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn

from kwik.settings import BaseKwikSettings

from .gunicorn import KwikGunicornApplication

if TYPE_CHECKING:
    from .kwik import Kwik


def run(kwik_app: str | Kwik) -> None:
    """
    Run a Kwik application using the optimal server configuration for the current environment.

    This function intelligently selects between Uvicorn (development) and Gunicorn (production)
    based on the APP_ENV setting, and handles both string module paths and Kwik application instances.

    Args:
        kwik_app: Either a string representing a module path containing a FastAPI 'app' attribute,
                 or a Kwik application instance with direct access to the underlying FastAPI app.

    Behavior:
        **String input (e.g., "myproject.main")**:
        - Constructs the app path as "{module_path}.app"
        - Enables hot-reload in development mode for file change detection
        - Suitable for running external applications or development workflows

        **Kwik instance input**:
        - Uses the pre-configured FastAPI app via kwik_app.app
        - Disables hot-reload (application already instantiated)
        - Typical for production deployments with pre-built applications

    Server Selection:
        - **Development (APP_ENV="development")**: Uvicorn with optimized settings:
          - HTTP tools for performance
          - WebSocket support enabled
          - Proxy headers handling
          - Hot-reload based on input type

        - **Production (APP_ENV="production")**: Gunicorn with KwikUvicornWorker:
          - Multi-process worker management
          - Optimized Uvicorn workers with HTTP tools and WebSocket support
          - Better resource utilization and fault tolerance

    Configuration Sources:
        - BACKEND_HOST, BACKEND_PORT: Server binding address
        - BACKEND_WORKERS: Number of worker processes
        - HOTRELOAD: Development hot-reload setting (overridden by input type)
        - LOG_LEVEL: Logging verbosity

    Note:
        This function blocks until the server is stopped. It's designed to be the main
        entry point for application execution.

    """
    settings = BaseKwikSettings()

    # Load server configuration from settings
    reload = settings.HOTRELOAD  # Base hot-reload setting from configuration
    workers = settings.BACKEND_WORKERS  # Number of worker processes

    # Determine application path and hot-reload behavior based on input type
    if isinstance(kwik_app, str):
        # String input: treat as module path and construct ASGI app path
        # Expected format: "myproject.main" -> "myproject.main.app"
        fastapi_app = f"{kwik_app}.app"
        # Keep reload setting from configuration (typically enabled in development)
    else:
        # Kwik instance input: use pre-configured FastAPI application
        fastapi_app = kwik_app.app
        # Disable reload for instantiated apps (cannot reload an already created object)
        reload = False

    # Select server based on environment configuration
    if settings.APP_ENV == "development":
        # Development mode: Use Uvicorn directly for simplicity and debugging
        uvicorn.run(
            fastapi_app,  # ASGI application (string path or callable)
            host=settings.BACKEND_HOST,  # Server host (default: localhost)
            port=settings.BACKEND_PORT,  # Server port (default: 8080)
            log_level=settings.LOG_LEVEL.lower(),  # Logging verbosity
            reload=reload,  # Hot-reload for development (file watching)
            http="httptools",  # Use httptools for better HTTP parsing performance
            proxy_headers=True,  # Handle X-Forwarded-* headers (reverse proxy support)
            workers=workers,  # Number of worker processes (usually 1 in development)
        )

    elif settings.APP_ENV == "production":
        # Production mode: Use Gunicorn with custom Uvicorn workers for better process management
        options = {
            # Server binding configuration (host:port format for Gunicorn)
            "bind": f"{settings.BACKEND_HOST}:{settings.BACKEND_PORT}",
            # Number of worker processes for handling concurrent requests
            "workers": workers,
            # Custom worker class with optimized Uvicorn configuration
            # (includes httptools, websockets, and proxy_headers automatically)
            "worker_class": "kwik.applications.uvicorn.KwikUvicornWorker",
        }

        # Initialize and run Gunicorn application with custom configuration
        KwikGunicornApplication(fastapi_app, options).run()

    else:
        msg = f"Unsupported APP_ENV: {settings.APP_ENV}. Must be 'development' or 'production'."
        raise ValueError(msg)
