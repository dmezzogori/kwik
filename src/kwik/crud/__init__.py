"""
CRUD operations package for kwik framework.

This package provides Create, Read, Update, Delete operations for database models,
including automatic CRUD generation and specialized operations for user management,
auditing, and permissions.
"""

from .audits import audit
from .auto_crud import AutoCRUD
from .logs import logs
from .permissions import permissions
from .roles import roles
from .roles_permissions import roles_permissions
from .user_roles import user_roles
from .users import users

__all__ = [
    "AutoCRUD",
    "audit",
    "logs",
    "permissions",
    "roles",
    "roles_permissions",
    "user_roles",
    "users",
]
