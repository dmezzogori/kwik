"""Schemas for authentication and login operations."""

from pydantic import BaseModel


class PasswordRecoveryRequest(BaseModel):
    """Schema for password recovery requests with user email."""

    email: str
