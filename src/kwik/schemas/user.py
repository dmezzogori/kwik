"""Pydantic schemas for user validation."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, EmailStr, model_validator
from pydantic.types import StringConstraints

from .mixins import ORMMixin

_UserName = Annotated[str, StringConstraints(min_length=1)]
_UserSurname = Annotated[str, StringConstraints(min_length=1)]


class UserRegistration(BaseModel):
    """Schema for new user registration with required fields."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    password: str
    is_active: bool = True


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile information."""

    name: _UserName | None = None
    surname: _UserSurname | None = None
    email: EmailStr | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UserProfileUpdate:
        """Ensure at least one field is provided for update."""
        provided_fields = [k for k, val in self.model_dump().items() if val is not None]
        if not provided_fields:
            msg = "At least one field must be provided for update"
            raise ValueError(msg)
        return self


class UserPasswordChange(BaseModel):
    """Schema for user password change requests."""

    old_password: str
    new_password: str


class UserProfile(ORMMixin):
    """Schema for user profile data."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    is_active: bool
