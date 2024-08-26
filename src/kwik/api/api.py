from kwik.routers import APIRouter

from . import endpoints

api_router = APIRouter()

api_router.include_many(package=endpoints)
