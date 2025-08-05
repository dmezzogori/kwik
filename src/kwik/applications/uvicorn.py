"""Uvicorn worker configuration for Kwik framework."""

from typing import ClassVar

from uvicorn.workers import UvicornWorker


class KwikUvicornWorker(UvicornWorker):
    """Uvicorn worker with optimized configuration for HTTP tools and WebSocket support."""

    CONFIG_KWARGS: ClassVar[dict[str, str | bool]] = {"http": "httptools", "ws": "websockets", "proxy_headers": True}
