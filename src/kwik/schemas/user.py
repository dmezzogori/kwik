"""Pydantic schemas for user validation."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, EmailStr
from pydantic.types import StringConstraints

from .mixins import AtLeastOneFieldMixin, ORMMixin

_UserName = Annotated[str, StringConstraints(min_length=1)]
_UserSurname = Annotated[str, StringConstraints(min_length=1)]


class UserRegistration(BaseModel):
    """Schema for new user registration with required fields."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    password: str
    is_active: bool = True


class UserProfileUpdate(AtLeastOneFieldMixin):
    """Schema for updating user profile information."""

    name: _UserName | None = None
    surname: _UserSurname | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


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
