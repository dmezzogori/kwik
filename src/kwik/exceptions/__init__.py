"""
Exception handling package for kwik framework.

This package contains custom exception classes and exception handlers
for proper error handling throughout the kwik web framework.
"""

from __future__ import annotations

from .base import AccessDeniedError, DuplicatedEntityError, EntityNotFoundError, KwikError
from .handler import kwik_exception_handler, value_error_handler
from .users import AuthenticationFailedError, InactiveUserError, UserNotFoundError

__all__ = [
    "AccessDeniedError",
    "AuthenticationFailedError",
    "DuplicatedEntityError",
    "EntityNotFoundError",
    "InactiveUserError",
    "KwikError",
    "UserNotFoundError",
    "kwik_exception_handler",
    "value_error_handler",
]
