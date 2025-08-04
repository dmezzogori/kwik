"""
CRUD operations package for kwik framework.

This package provides Create, Read, Update, Delete operations for database models,
including automatic CRUD generation and specialized operations for user management,
auditing, and permissions.
"""

from .audits import audit
from .auto_crud import AutoCRUD
from .permissions import permissions
from .roles import roles
from .users import users

__all__ = [
    "AutoCRUD",
    "audit",
    "permissions",
    "roles",
    "users",
]
