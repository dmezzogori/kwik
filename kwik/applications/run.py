from __future__ import annotations

import uvicorn
from kwik import settings
from kwik.applications.gunicorn import KwikGunicornApplication

from .kwik import Kwik


def run(kwik_app: str | Kwik) -> None:
    reload = settings.HOTRELOAD
    workers = settings.BACKEND_WORKERS
    if isinstance(kwik_app, str):
        kwik_app = f"{kwik_app}._app"
    else:
        kwik_app = kwik_app._app
        reload = False

    if settings.APP_ENV == "development":
        uvicorn.run(
            kwik_app,
            host=settings.BACKEND_HOST,
            port=settings.BACKEND_PORT,
            log_level=settings.LOG_LEVEL.lower(),
            reload=reload,
            http="httptools",
            ws="websockets",
            proxy_headers=True,
            workers=workers,
        )
    else:
        options = {
            "bind": f"{settings.BACKEND_HOST}:{settings.BACKEND_PORT}",
            "workers": workers,
            "worker_class": "kwik.applications.uvicorn.KwikUvicornWorker",
        }
        KwikGunicornApplication(kwik_app, options).run()
