"""
API package for kwik framework.

This package contains FastAPI route definitions and API endpoints
for the kwik web framework.
"""

from __future__ import annotations

from .api import api_router, build_api_router

__all__ = ["api_router", "build_api_router"]
