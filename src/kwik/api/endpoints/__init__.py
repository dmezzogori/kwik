"""
API endpoints package for kwik framework.

This package contains FastAPI endpoint factories and routers for the kwik web framework.
"""

from __future__ import annotations

from .login import create_login_router
from .permissions import permissions_router
from .roles import create_roles_router
from .users import create_users_router

__all__ = ["create_login_router", "create_roles_router", "create_users_router", "permissions_router"]
