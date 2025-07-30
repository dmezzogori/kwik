"""isort:skip_file."""
from __future__ import annotations

from .core.config import Settings

# Initialize settings before importing modules that depend on it
settings = Settings()

from . import utils  # noqa: E402
from .api.api import api_router  # noqa: E402
from .api.deps import (  # noqa: E402
    FilterQuery,
    PaginatedQuery,
    SortingQuery,
    current_user,
    has_permission,
)
from .applications import Kwik, run  # noqa: E402
from .database.session import KwikQuery, KwikSession  # noqa: E402
from .exporters.base import KwikExporter  # noqa: E402
from .logger import logger  # noqa: E402
from .routers.autorouter import AutoRouter  # noqa: E402
from .websocket.deps import broadcast  # noqa: E402

__all__ = [
    "AutoRouter",
    "FilterQuery",
    "Kwik",
    "KwikExporter",
    "KwikQuery",
    "KwikSession",
    "PaginatedQuery",
    "SortingQuery",
    "api_router",
    "broadcast",
    "current_user",
    "has_permission",
    "logger",
    "run",
    "settings",
    "utils",
]
