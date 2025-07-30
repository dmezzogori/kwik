"""Database package for kwik framework.

This package provides database connectivity, session management, and context handling
for the kwik web framework. It includes async PostgreSQL support via SQLAlchemy.
"""

from __future__ import annotations

from . import base, mixins, session
from .current_user_context_manager import CurrentUserContextManager
from .db_context_manager import DBContextManager
from .db_context_switcher import DBContextSwitcher

__all__ = [
    "CurrentUserContextManager",
    "DBContextManager",
    "DBContextSwitcher",
    "base",
    "mixins",
    "session",
]
