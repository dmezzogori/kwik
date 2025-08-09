"""
CRUD operations package for kwik framework.

This package provides Create, Read, Update, Delete operations for database models,
including automatic CRUD generation and specialized operations for user management,
auditing, and permissions.
"""

from .audits import crud_audit
from .autocrud import AutoCRUD, Context, MaybeUserCtx, NoDatabaseConnectionError, NoUserCtx, UserCtx
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
    "crud_audit",
    "crud_permissions",
    "crud_roles",
    "crud_users",
]
