"""Pydantic schemas for user validation."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr
from pydantic.types import StringConstraints

from kwik.core import BCRYPT_MAX_PASSWORD_BYTES

from .mixins import AtLeastOneFieldMixin, ORMMixin

_UserName = Annotated[str, StringConstraints(min_length=1)]
_UserSurname = Annotated[str, StringConstraints(min_length=1)]


def _within_bcrypt_limit(value: str) -> str:
    """
    Reject passwords whose UTF-8 encoding exceeds what bcrypt will hash.

    The bound is on *bytes*, not characters: a 72-character string of multi-byte
    characters encodes to more than 72 bytes, so ``StringConstraints(max_length=...)``
    would let it through and bcrypt >=5.0.0 would then raise.
    """
    encoded_length = len(value.encode("utf-8"))
    if encoded_length > BCRYPT_MAX_PASSWORD_BYTES:
        msg = f"password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        raise ValueError(msg)
    return value


# Applied to passwords being *set*. Passwords being *verified* stay unconstrained:
# an account created under bcrypt <5.0.0 may hold a longer secret, and rejecting it
# at validation time would turn a failed login into a confusing 422.
_NewPassword = Annotated[str, AfterValidator(_within_bcrypt_limit)]


class UserRegistration(BaseModel):
    """Schema for new user registration with required fields."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    password: _NewPassword
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
    new_password: _NewPassword


class AdminPasswordReset(BaseModel):
    """Schema for admin-initiated password reset (no old password required)."""

    new_password: _NewPassword


class UserProfile(ORMMixin):
    """Schema for user profile data."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    is_active: bool
