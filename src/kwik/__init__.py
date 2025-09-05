"""
Kwik - A modern, batteries-included web framework for building RESTful backends with Python.

Kwik is built on FastAPI and provides an opinionated, business-oriented API for rapid development.

The testing module provides enhanced testing utilities for Kwik applications:
    from kwik.testing import Scenario, IdentityAwareTestClient
"""

from __future__ import annotations

from . import testing
from .api.api import api_router
from .applications import Kwik, run

__all__ = ["Kwik", "api_router", "run", "testing"]
