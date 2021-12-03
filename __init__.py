from . import core

settings = None


def set_settings(**kwargs):
    global settings
    if kwargs:
        settings = core.config.Settings.construct(**kwargs)
    else:
        settings = core.config.Settings()


set_settings(POSTGRES_PASSWORD="fake")


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

from . import core
from . import crud
from . import exceptions
from . import middlewares
from . import models
from . import routers
from . import schemas
from . import typings
from . import utils
from .api.api import api_router
from .logging import logger
from .routers.autorouter import AutoRouter
from .websocket.deps import broadcast
