"""
Main API router configuration for the Kwik framework.

This module sets up the main API router by including all endpoint routers from the endpoints package.
"""

from kwik.routers import APIRouter

from .endpoints.login import router as login_router
from .endpoints.users import router as users_router

api_router = APIRouter()

api_router.include_router(login_router)
api_router.include_router(users_router)
