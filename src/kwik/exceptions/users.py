"""Exception classes for users functionality."""

from fastapi import status

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
