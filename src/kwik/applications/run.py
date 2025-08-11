"""Kwik application runner with multiple server options."""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn

from kwik.applications.gunicorn import KwikGunicornApplication
from kwik.core.settings import get_settings

if TYPE_CHECKING:
    from .kwik import Kwik


# TODO: implement run function as a (class)method of Kwik class
def run(kwik_app: str | Kwik) -> None:
    """Run Kwik application with appropriate server based on environment."""
    reload = get_settings().HOTRELOAD
    workers = get_settings().BACKEND_WORKERS

    if isinstance(kwik_app, str):
        fastapi_app = f"{kwik_app}.app"
    else:
        fastapi_app = kwik_app.app
        reload = False

    if get_settings().APP_ENV == "development":
        uvicorn.run(
            fastapi_app,
            host=get_settings().BACKEND_HOST,
            port=get_settings().BACKEND_PORT,
            log_level=get_settings().LOG_LEVEL.lower(),
            reload=reload,
            http="httptools",
            ws="websockets",
            proxy_headers=True,
            workers=workers,
        )
    else:
        options = {
            "bind": f"{get_settings().BACKEND_HOST}:{get_settings().BACKEND_PORT}",
            "workers": workers,
            "worker_class": "kwik.applications.uvicorn.KwikUvicornWorker",
        }
        KwikGunicornApplication(fastapi_app, options).run()
