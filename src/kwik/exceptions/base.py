"""Base exception classes for Kwik framework."""

from __future__ import annotations

from fastapi import HTTPException, status


class KwikException(Exception):
    """Base class for all Kwik exceptions."""

    def __init__(self, status_code: int, detail: str) -> None:
        """Initialize Kwik exception with status code and detail message."""
        self.status_code: int = status_code
        self.detail: str = detail
        super().__init__()

    @property
    def http_exc(self):
        """Convert Kwik exception to FastAPI HTTPException."""
        return HTTPException(status_code=self.status_code, detail=self.detail)


class DuplicatedEntity(KwikException):
    """Exception raised when attempting to create a duplicate entity."""

    def __init__(self, detail="Entity already exists"):
        """Initialize duplicated entity exception with custom detail message."""
        super().__init__(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=detail)


class Forbidden(KwikException):
    """Exception raised when user lacks required privileges for an operation."""

    def __init__(self, detail="Not enough privileges"):
        """Initialize forbidden access exception with custom detail message."""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFound(KwikException):
    """Exception raised when requested entity is not found."""

    def __init__(self, detail="Entity not found"):
        """Initialize not found exception with custom detail message."""
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InvalidToken(KwikException):
    """Exception raised when authentication token is invalid or expired."""

    def __init__(self, detail="Invalid token"):
        """Initialize invalid token exception with custom detail message."""
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
