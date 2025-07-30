"""Uvicorn worker configuration for Kwik framework."""

from uvicorn.workers import UvicornWorker


class KwikUvicornWorker(UvicornWorker):
    """Uvicorn worker with optimized configuration for HTTP tools and WebSocket support."""

    CONFIG_KWARGS = {"http": "httptools", "ws": "websockets", "proxy_headers": True}
