"""CRUD operations package for kwik framework.

This package provides Create, Read, Update, Delete operations for database models,
including automatic CRUD generation and specialized operations for user management,
auditing, and permissions.
"""

from .audits import audit
from .auto_crud import AutoCRUD
from .logs import logs
from .permissions import permission
from .roles import role
from .roles_permissions import roles_permissions
from .user_roles import user_roles
from .users import user

__all__ = [
    "AutoCRUD",
    "audit",
    "logs",
    "permission",
    "role",
    "roles_permissions",
    "user",
    "user_roles",
]
