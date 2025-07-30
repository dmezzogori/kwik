"""Exception handling package for kwik framework.

This package contains custom exception classes and exception handlers
for proper error handling throughout the kwik web framework.
"""

from __future__ import annotations

from .base import DuplicatedEntity, Forbidden, KwikException, NotFound
from .exporters import ExporterLimitExceeded
from .handler import kwik_exception_handler
from .users import IncorrectCredentials, UserInactive, UserNotFound

__all__ = [
    "DuplicatedEntity",
    "ExporterLimitExceeded",
    "Forbidden",
    "IncorrectCredentials",
    "KwikException",
    "NotFound",
    "UserInactive",
    "UserNotFound",
    "kwik_exception_handler",
]
