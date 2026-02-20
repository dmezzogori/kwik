"""Enumerations for Kwik framework permissions and core types."""

from __future__ import annotations

from enum import StrEnum


class PermissionNamesBase(StrEnum):
    """Base class for defining permission name enumerations."""


class Permissions(StrEnum):
    """System-wide permission definitions for user access control."""

    impersonification = "impersonification"

    user_create = "user_create"
    user_read = "user_read"
    user_update = "user_update"
    user_delete = "user_delete"

    permission_create = "permission_create"
    permission_read = "permission_read"
    permission_update = "permission_update"
    permission_delete = "permission_delete"

    role_create = "role_create"
    role_read = "role_read"
    role_update = "role_update"
    role_delete = "role_delete"
