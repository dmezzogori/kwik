from enum import Enum


class PermissionNamesBase(Enum):
    def __repr__(self):
        return str(self.value)


class PermissionNames(PermissionNamesBase):
    impersonification = "impersonification"
    user_management = "user_management"
