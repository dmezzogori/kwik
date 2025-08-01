"""
Pydantic schemas package for kwik framework.

This package contains Pydantic models for request/response validation, data serialization,
and API schema definitions across the kwik web framework.
"""

from __future__ import annotations

from . import role_permissions
from .audit import AuditCreateSchema, AuditORMSchema
from .login import RecoverPassword
from .logs import LogCreateSchema, LogORMSchema
from .mixins.orm import ORMMixin
from .mixins.record_info import RecordInfoMixin
from .pagination import Paginated
from .permission import PermissionCreate, PermissionORMSchema, PermissionUpdate
from .role import Role, RoleCreate, RoleInDB, RoleUpdate, UserRoleCreate, UserRoleRemove
from .token import Token, TokenPayload
from .user import (
    UserChangePasswordSchema,
    UserCreateSchema,
    UserORMExtendedSchema,
    UserORMSchema,
    UserUpdateSchema,
)

__all__ = [
    "AuditCreateSchema",
    "AuditORMSchema",
    "LogCreateSchema",
    "LogORMSchema",
    "ORMMixin",
    "Paginated",
    "PermissionCreate",
    "PermissionORMSchema",
    "PermissionUpdate",
    "RecordInfoMixin",
    "RecoverPassword",
    "Role",
    "RoleCreate",
    "RoleInDB",
    "RoleUpdate",
    "Token",
    "TokenPayload",
    "UserChangePasswordSchema",
    "UserCreateSchema",
    "UserORMExtendedSchema",
    "UserORMSchema",
    "UserRoleCreate",
    "UserRoleRemove",
    "UserUpdateSchema",
    "role_permissions",
]
