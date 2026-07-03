"""
Data models package for kwik framework.

This package contains SQLAlchemy models for user management
functionality within the kwik web framework.
"""

from .api_key import ApiKey
from .base import Base

# TRANSITIONAL (removed before release): keeps `from kwik.models import User` working
# during the incremental 2.0 migration. Eagerly maps DefaultUser.
from .default_user import DefaultUser as User
from .mixins import RecordInfoMixin, TimeStampsMixin, UserTrackingMixin
from .user import Permission, Role, RolePermission, UserRole
from .user_mixin import UserMixin

__all__ = [
    "ApiKey",
    "Base",
    "Permission",
    "RecordInfoMixin",
    "Role",
    "RolePermission",
    "TimeStampsMixin",
    "User",
    "UserMixin",
    "UserRole",
    "UserTrackingMixin",
]
