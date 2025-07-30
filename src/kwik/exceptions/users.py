"""Exception classes for users functionality."""

from fastapi import status

from .base import KwikException


class IncorrectCredentials(KwikException):
    """Exception raised when user provides incorrect login credentials."""

    def __init__(self, detail="Incorrect credentials"):
        """Initialize incorrect credentials exception with custom detail message."""
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class UserNotFound(KwikException):
    """Exception raised when requested user does not exist."""

    def __init__(self, detail="User not found"):
        """Initialize user not found exception with custom detail message."""
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UserInactive(KwikException):
    """Exception raised when attempting to authenticate inactive user."""

    def __init__(self, detail="Inactive user"):
        """Initialize inactive user exception with custom detail message."""
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
