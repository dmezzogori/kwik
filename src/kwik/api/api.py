"""
Main API router configuration for the Kwik framework.

This module sets up the main API router by including all endpoint routers from the endpoints package.
"""

from fastapi import APIRouter

from .endpoints import context_router, login_router, permissions_router, roles_router, users_router

api_router = APIRouter()

api_router.include_router(login_router)
api_router.include_router(context_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)

__all__ = ["api_router"]
