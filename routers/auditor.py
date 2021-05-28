import time
from typing import Callable, Optional

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from jose import jwt

from app.kwik import models, schemas
from app.kwik.api.deps import get_current_user
from app.kwik.core import security
from app.kwik.core.config import settings
from app.kwik.db.session import DBContextManager


class KwikRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            self._body = body
        return self._body

    @property
    def token(self) -> Optional[str]:
        auth = self.headers.get('Authorization')
        if auth is not None and 'Bearer ' in auth:
            return auth.replace('Bearer ', '')
        return None


class AuditorRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            start = time.time()
            request = KwikRequest(request.scope, request.receive)
            body = await request.body()
            response: Response = await original_route_handler(request)
            process_time = time.time() - start
            response.headers["X-Response-Time"] = str(process_time)

            with DBContextManager() as db:

                user_id = None
                impersonator_user_id = None
                if request.token is not None:
                    user = get_current_user(db, request.token)
                    user_id = user.id

                    payload = jwt.decode(
                        request.token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
                    )
                    token_data = schemas.TokenPayload(**payload)

                    if token_data.kwik_impersonate != '':
                        impersonator_user_id = int(token_data.kwik_impersonate)

                audit_db = models.Audit(
                    client_host=request.client.host,
                    user_id=user_id,
                    impersonator_user_id=impersonator_user_id,
                    method=request.method,
                    headers=repr(request.headers),
                    url=request.url.path,
                    query_params=repr(request.query_params),
                    path_params=repr(request.path_params),
                    body=str(body),
                    process_time=process_time*1000,
                    status_code=response.status_code
                )
                db.add(audit_db)
                db.commit()

            return response

        return custom_route_handler


def AuditorRouter():
    return APIRouter(route_class=AuditorRoute)
