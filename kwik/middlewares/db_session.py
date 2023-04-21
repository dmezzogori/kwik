import kwik.crud.base
from kwik.database.db_context_manager import DBContextManager
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        with DBContextManager(settings=kwik.settings) as db:
            request.state.db = db
            response = await call_next(request)

        return response
