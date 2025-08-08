"""
API endpoints package for kwik framework.

This package contains FastAPI endpoint implementations for various
API routes within the kwik web framework.
"""

from __future__ import annotations

from .login import login_router
from .permissions import permissions_router
from .roles import roles_router
from .users import users_router

__all__ = ["login_router", "permissions_router", "roles_router", "users_router"]
