# ATTENZIONE ALL'ORDINE DI IMPORT

from .core.config import Settings

settings = Settings()

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
from .applications import Kwik, run, set_running_app, get_running_app

_running_app = None
