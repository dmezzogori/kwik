from uvicorn.workers import UvicornWorker


class KwikUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {"http": "httptools", "ws": "websockets", "proxy_headers": True}
