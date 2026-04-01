"""
API dependencies package for kwik framework.

This package contains FastAPI dependency providers for authentication,
database access, and other common API requirements.
"""

from __future__ import annotations

from .api_key import ApiKeyContext, verify_api_key
from .context import NoUserContext, UserContext
from .filter_query import Filters
from .list_query import ListQuery
from .pagination import Pagination
from .permissions import has_permission
from .session import Session
from .settings import Settings
from .sorting_query import Sorting
from .token import current_token
from .users import current_user, resolved_user

__all__ = [
    "ApiKeyContext",
    "Filters",
    "ListQuery",
    "NoUserContext",
    "Pagination",
    "Session",
    "Settings",
    "Sorting",
    "UserContext",
    "current_token",
    "current_user",
    "has_permission",
    "resolved_user",
    "verify_api_key",
]
