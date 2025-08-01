"""
Main API router configuration for the Kwik framework.

This module sets up the main API router by including all endpoint routers from the endpoints package.
"""

from kwik.routers import APIRouter

from . import endpoints

api_router = APIRouter()

api_router.include_many(package=endpoints)
