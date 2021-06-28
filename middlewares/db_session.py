from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from app.kwik.db.session import DBContextManager


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        with DBContextManager() as db:
            request.state.db = db
            response = await call_next(request)
        return response
