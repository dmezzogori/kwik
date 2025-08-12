"""
Kwik - A modern, batteries-included web framework for building RESTful backends with Python.

Kwik is built on FastAPI and provides an opinionated, business-oriented API for rapid development.
"""

from __future__ import annotations

from .api.api import api_router
from .applications import Kwik, run

__all__ = ["Kwik", "api_router", "run"]
