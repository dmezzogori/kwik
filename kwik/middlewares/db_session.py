from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from kwik.database.session import DBContextManager
import kwik.crud.base


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        with DBContextManager(settings=kwik.settings) as db:

            kwik.crud.base.CRUDBase.db = db

            request.state.db = db
            response = await call_next(request)

        kwik.crud.base.CRUDBase.db = None

        return response
