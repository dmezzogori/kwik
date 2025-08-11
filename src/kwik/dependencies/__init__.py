"""
API dependencies package for kwik framework.

This package contains FastAPI dependency providers for authentication,
database access, and other common API requirements.
"""

from __future__ import annotations

from .context import NoUserContext, UserContext
from .filter_query import FilterQuery
from .pagination import Pagination
from .permissions import has_permission
from .session import Session
from .settings import Settings
from .sorting_query import SortingQuery
from .token import current_token
from .users import current_user

__all__ = [
    "FilterQuery",
    "NoUserContext",
    "Pagination",
    "Session",
    "Settings",
    "SortingQuery",
    "UserContext",
    "current_token",
    "current_user",
    "has_permission",
]
