from enum import StrEnum


class PermissionNamesBase(StrEnum):
    pass


class PermissionNames(PermissionNamesBase):
    impersonification = "impersonification"
    user_management = "user_management"
