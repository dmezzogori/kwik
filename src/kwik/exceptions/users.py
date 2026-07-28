"""Exception classes for users functionality."""

from fastapi import status

from kwik.core import BCRYPT_MAX_PASSWORD_BYTES

from .base import KwikError


class AuthenticationFailedError(KwikError):
    """Exception raised when user provides incorrect login credentials."""

    def __init__(self, detail: str = "Incorrect credentials") -> None:
        """Initialize incorrect credentials exception with custom detail message."""
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class UserNotFoundError(KwikError):
    """Exception raised when requested user does not exist."""

    def __init__(self, detail: str = "User not found") -> None:
        """Initialize user not found exception with custom detail message."""
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InactiveUserError(KwikError):
    """Exception raised when attempting to authenticate inactive user."""

    def __init__(self, detail: str = "Inactive user") -> None:
        """Initialize inactive user exception with custom detail message."""
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class PasswordTooLongError(KwikError):
    """Exception raised when a password exceeds the byte length bcrypt accepts."""

    def __init__(self, actual_bytes: int | None = None) -> None:
        """Initialize password-too-long exception, optionally reporting the actual size."""
        detail = f"Password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded"
        if actual_bytes is not None:
            detail = f"{detail} (got {actual_bytes})"
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)
