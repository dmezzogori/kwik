"""
CRUD operations package for kwik framework.

This package provides Create, Read, Update, Delete operations for database models,
including automatic CRUD generation and specialized operations for user management and permissions.
"""

from .autocrud import AutoCRUD, NoDatabaseConnectionError
from .context import Context, MaybeUserCtx, NoUserCtx, UserCtx
from .permissions import crud_permissions
from .roles import crud_roles
from .users import crud_users

__all__ = [
    "AutoCRUD",
    "Context",
    "MaybeUserCtx",
    "NoDatabaseConnectionError",
    "NoUserCtx",
    "UserCtx",
    "crud_permissions",
    "crud_roles",
    "crud_users",
]
