"""Uvicorn worker configuration for Kwik framework."""

from typing import Any, ClassVar

from uvicorn_worker import UvicornWorker

GRACEFUL_SHUTDOWN_MARGIN = 5
"""Seconds left between uvicorn's shutdown deadline and gunicorn's SIGKILL.

Covers the cleanup that cancelled tasks run (for example a stream's shielded lease
release) and the lifespan shutdown."""


class KwikUvicornWorker(UvicornWorker):
    """Uvicorn worker with optimized configuration for HTTP tools and WebSocket support."""

    CONFIG_KWARGS: ClassVar[dict[str, str | bool]] = {"http": "httptools", "ws": "websockets", "proxy_headers": True}

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """
        Build the worker and bound uvicorn's graceful shutdown by gunicorn's.

        Without a bound, uvicorn waits on open streaming responses until gunicorn
        SIGKILLs the worker after ``graceful_timeout``, and the streams' cleanup
        never runs. Deriving the value from gunicorn's keeps the two in step,
        whatever ``graceful_timeout`` the application configures.
        """
        super().__init__(*args, **kwargs)
        self.config.timeout_graceful_shutdown = max(int(self.cfg.graceful_timeout) - GRACEFUL_SHUTDOWN_MARGIN, 1)
