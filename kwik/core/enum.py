from __future__ import annotations

from enum import StrEnum


class PermissionNamesBase(StrEnum):
    pass


class Permissions(StrEnum):
    impersonification = "impersonification"

    user_management_create = "user_management_create"
    user_management_read = "user_management_read"
    user_management_update = "user_management_update"
    user_management_delete = "user_management_delete"

    permissions_management_create = "permissions_management_create"
    permissions_management_read = "permissions_management_read"
    permissions_management_update = "permissions_management_update"
    permissions_management_delete = "permissions_management_delete"

    roles_management_create = "roles_management_create"
    roles_management_read = "roles_management_read"
    roles_management_update = "roles_management_update"
    roles_management_delete = "roles_management_delete"
