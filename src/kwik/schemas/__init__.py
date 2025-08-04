"""
Pydantic schemas package for kwik framework.

This package contains Pydantic models for request/response validation, data serialization,
and API schema definitions across the kwik web framework.
"""

from __future__ import annotations

from . import role_permissions
from .audit import AuditEntry, AuditProfile
from .login import PasswordRecoveryRequest
from .logs import LogEntry, LogProfile
from .mixins.orm import ORMMixin
from .mixins.record_info import RecordInfoMixin
from .pagination import Paginated
from .permission import PermissionDefinition, PermissionProfile, PermissionRoleAssignment, PermissionUpdate
from .role import RoleDefinition, RoleInDB, RoleProfile, RoleUpdate, UserRoleAssignment, UserRoleRevocation
from .token import Token, TokenPayload
from .user import (
    UserAuthenticationInfo,
    UserPasswordChange,
    UserProfile,
    UserProfileUpdate,
    UserRegistration,
)

__all__ = [
    "AuditEntry",
    "AuditProfile",
    "LogEntry",
    "LogProfile",
    "ORMMixin",
    "Paginated",
    "PasswordRecoveryRequest",
    "PermissionDefinition",
    "PermissionProfile",
    "PermissionRoleAssignment",
    "PermissionUpdate",
    "RecordInfoMixin",
    "RoleDefinition",
    "RoleInDB",
    "RoleProfile",
    "RoleUpdate",
    "Token",
    "TokenPayload",
    "UserAuthenticationInfo",
    "UserPasswordChange",
    "UserProfile",
    "UserProfileUpdate",
    "UserRegistration",
    "UserRoleAssignment",
    "UserRoleRevocation",
    "role_permissions",
]
