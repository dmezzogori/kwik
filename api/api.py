from fastapi import APIRouter

from .endpoints import login, users, utils, roles, permissions
from .deps import has_permission

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"]) # , dependencies=[has_permission("cia")]
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
