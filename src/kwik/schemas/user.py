"""Pydantic schemas for user validation."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, ValidationInfo
from pydantic.types import StringConstraints

from kwik.core import BCRYPT_MAX_PASSWORD_BYTES
from kwik.core.password_policy import password_min_length

from .mixins import AtLeastOneFieldMixin, ORMMixin

_UserName = Annotated[str, StringConstraints(min_length=1)]
_UserSurname = Annotated[str, StringConstraints(min_length=1)]


PASSWORD_POLICY_CONTEXT_KEY = "password_policy"  # noqa: S105 - a context key, not a secret
"""Validation-context key that, set to ``False``, skips the minimum length.

For seeds and scripts that create accounts from configuration, such as the first
superuser: ``UserRegistration.model_validate(data, context={"password_policy": False})``."""


def _new_password(value: str, info: ValidationInfo) -> str:
    """
    Check a password being set: the configured minimum length, and what bcrypt will hash.

    The minimum counts characters and follows NIST SP 800-63B: length only, no
    composition rules. It is skipped when the validation context carries
    ``{"password_policy": False}``; the bcrypt bound always applies.

    The bcrypt bound is on *bytes*, not characters: a 72-character string of multi-byte
    characters encodes to more than 72 bytes, so ``StringConstraints(max_length=...)``
    would let it through and bcrypt >=5.0.0 would then raise.
    """
    enforce_policy = (info.context or {}).get(PASSWORD_POLICY_CONTEXT_KEY, True)
    min_length = password_min_length()
    if enforce_policy and len(value) < min_length:
        msg = f"password must be at least {min_length} characters"
        raise ValueError(msg)
    encoded_length = len(value.encode("utf-8"))
    if encoded_length > BCRYPT_MAX_PASSWORD_BYTES:
        msg = f"password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        raise ValueError(msg)
    return value


NewPassword = Annotated[str, AfterValidator(_new_password)]
"""A password being *set*: at least the configured minimum length, at most what bcrypt will hash.

The minimum is ``PASSWORD_MIN_LENGTH`` characters (12 by default), configured by
``Kwik`` at startup; validating with ``context={"password_policy": False}`` skips it
for accounts created from configuration.

Public so downstream schemas that collect a password and forward it to kwik can
apply the same bounds at *their* request boundary. Without it the constraint fires
only when kwik builds its own schema deeper in the call stack, where a Pydantic
``ValidationError`` surfaces as a 500 rather than a 422.

Passwords being *verified* stay unconstrained: an account created under
bcrypt <5.0.0 may hold a longer secret, and rejecting it at validation time would
turn a failed login into a confusing 422.
"""


class UserRegistration(BaseModel):
    """Schema for new user registration with required fields."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    password: NewPassword
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
    new_password: NewPassword


class AdminPasswordReset(BaseModel):
    """Schema for admin-initiated password reset (no old password required)."""

    new_password: NewPassword


class UserProfile(ORMMixin):
    """Schema for user profile data."""

    name: _UserName
    surname: _UserSurname
    email: EmailStr
    is_active: bool
