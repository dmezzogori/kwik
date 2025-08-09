"""
Kwik - A modern, batteries-included web framework for building RESTful backends with Python.

Kwik is built on FastAPI and provides an opinionated, business-oriented API for rapid development.
"""

from __future__ import annotations

from . import database, utils
from .api.api import api_router
from .api.deps import (
    FilterQuery,
    Pagination,
    SortingQuery,
    current_user,
    has_permission,
)
from .applications import Kwik, run
from .core.settings import BaseKwikSettings, configure_kwik, get_settings
from .logger import logger

__all__ = [
    "BaseKwikSettings",
    "FilterQuery",
    "Kwik",
    "Pagination",
    "SortingQuery",
    "api_router",
    "configure_kwik",
    "current_user",
    "database",
    "get_settings",
    "has_permission",
    "logger",
    "run",
    "utils",
]
