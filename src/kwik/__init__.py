"""
Kwik - A modern, batteries-included web framework for building RESTful backends with Python.

Kwik is built on FastAPI and provides an opinionated, business-oriented API for rapid development.

Consuming applications register their user model once via ``kwik.Kernel`` and build
the API router from it::

    kernel = kwik.Kernel(user_model=AppUser, schemas=kwik.UserSchemas(...))
    app = kwik.Kwik(settings=Settings(), api_router=kernel.create_api_router())

The testing module provides enhanced testing utilities for Kwik applications:
    from kwik.testing import Scenario, IdentityAwareTestClient
"""

from __future__ import annotations

from . import testing
from .applications import Kwik, run
from .dependencies import NoUserContext, UserContext, current_user, resolved_user
from .kernel import Kernel, UserSchemas
from .models.user_mixin import UserMixin

__all__ = [
    "Kernel",
    "Kwik",
    "NoUserContext",
    "UserContext",
    "UserMixin",
    "UserSchemas",
    "current_user",
    "resolved_user",
    "run",
    "testing",
]
