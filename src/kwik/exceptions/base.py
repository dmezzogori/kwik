"""Base exception classes for Kwik framework."""

from __future__ import annotations

from fastapi import HTTPException, status


class KwikError(Exception):
    """Base class for all Kwik exceptions."""

    def __init__(self, status_code: int, detail: str) -> None:
        """Initialize Kwik exception with status code and detail message."""
        self.status_code = status_code
        self.detail = detail
        super().__init__()

    @property
    def http_exc(self) -> HTTPException:
        """Convert Kwik exception to FastAPI HTTPException."""
        return HTTPException(status_code=self.status_code, detail=self.detail)


class DuplicatedEntityError(KwikError):
    """Exception raised when attempting to create a duplicate entity."""

    def __init__(self, detail: str = "Entity already exists") -> None:
        """Initialize duplicated entity exception with custom detail message."""
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class AccessDeniedError(KwikError):
    """Exception raised when user lacks required privileges for an operation."""

    def __init__(self, detail: str = "Not enough privileges") -> None:
        """Initialize forbidden access exception with custom detail message."""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class EntityNotFoundError(KwikError):
    """Exception raised when requested entity is not found."""

    def __init__(self, detail: str = "Entity not found") -> None:
        """Initialize not found exception with custom detail message."""
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class TokenValidationError(KwikError):
    """Exception raised when authentication token is invalid or expired."""

    def __init__(self, detail: str = "Invalid token") -> None:
        """Initialize invalid token exception with custom detail message."""
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
