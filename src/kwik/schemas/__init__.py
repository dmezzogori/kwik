"""
Pydantic schemas package for kwik framework.

This package contains Pydantic models for request/response validation, data serialization,
and API schema definitions across the kwik web framework.
"""

from __future__ import annotations

from .mixins import ORMMixin, RecordInfoMixin
from .pagination import Paginated
from .permission import PermissionDefinition, PermissionProfile, PermissionUpdate
from .role import RoleDefinition, RolePermissionAssignment, RoleProfile, RoleUpdate, RoleUserAssignment
from .token import Token, TokenPayload
from .user import (
    UserPasswordChange,
    UserProfile,
    UserProfileUpdate,
    UserRegistration,
)

__all__ = [
    "ORMMixin",
    "Paginated",
    "PermissionDefinition",
    "PermissionProfile",
    "PermissionUpdate",
    "RecordInfoMixin",
    "RoleDefinition",
    "RolePermissionAssignment",
    "RoleProfile",
    "RoleUpdate",
    "RoleUserAssignment",
    "Token",
    "TokenPayload",
    "UserPasswordChange",
    "UserProfile",
    "UserProfileUpdate",
    "UserRegistration",
]
