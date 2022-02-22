from .core.config import Settings

settings = Settings()


# ATTENZIONE ALL'ORDINE DI IMPORT
# LE DEPS DEVONO SEMPRE VENIRE PER PRIME
from .api.deps import (
    FilterQuery,
    PaginatedQuery,
    SortingQuery,
    current_active_superuser,
    current_active_user,
    current_user,
    db,
    has_permission,
)

from .api.api import api_router
from .logging import logger
from .routers.autorouter import AutoRouter
from .websocket.deps import broadcast

from .applications import Kwik


def run(kwik_app: str | Kwik):
    import uvicorn

    reload = settings.HOTRELOAD
    if isinstance(kwik_app, str):
        kwik_app = f"{kwik_app}._app"
    else:
        reload = False

    uvicorn.run(
        kwik_app, host=settings.HOST, port=settings.PORT, log_level=settings.LOG_LEVEL.lower(), reload=reload,
    )
