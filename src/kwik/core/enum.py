"""Enumerations for Kwik framework permissions and core types."""

from __future__ import annotations

from enum import StrEnum


class PermissionNamesBase(StrEnum):
    """Base class for defining permission name enumerations."""


class Permissions(StrEnum):
    """System-wide permission definitions for user access control."""

    impersonification = "impersonification"

    users_management_create = "users_management_create"
    users_management_read = "users_management_read"
    users_management_update = "users_management_update"
    users_management_delete = "users_management_delete"

    permissions_management_create = "permissions_management_create"
    permissions_management_read = "permissions_management_read"
    permissions_management_update = "permissions_management_update"
    permissions_management_delete = "permissions_management_delete"

    roles_management_create = "roles_management_create"
    roles_management_read = "roles_management_read"
    roles_management_update = "roles_management_update"
    roles_management_delete = "roles_management_delete"

    password_management_update = "password_management_update"  # noqa: S105
