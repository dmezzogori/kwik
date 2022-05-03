import time
from typing import Callable, Optional

import kwik
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from jose import jwt
from kwik import crud, schemas
from kwik.api.deps import get_current_user
from kwik.core import security
from kwik.database.session import get_db_from_request
from kwik.middlewares import get_request_id


class KwikRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            self._body = body
        return self._body

    @property
    def token(self) -> Optional[str]:
        auth = self.headers.get("Authorization")
        if auth is not None and "Bearer " in auth:
            return auth.replace("Bearer ", "")
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

            _running_app = kwik.get_running_app()
            if _running_app.dependency_overrides.get(get_db_from_request):
                db = list(_running_app.dependency_overrides.get(get_db_from_request)())[0]
            else:
                db = get_db_from_request(request)

            user_id = None
            impersonator_user_id = None
            if request.token is not None:
                user = get_current_user(db, request.token)
                user_id = user.id

                payload = jwt.decode(request.token, kwik.settings.SECRET_KEY, algorithms=[security.ALGORITHM])
                token_data = schemas.TokenPayload(**payload)

                if token_data.kwik_impersonate != "":
                    impersonator_user_id = int(token_data.kwik_impersonate)

            audit_in = schemas.AuditCreateSchema(
                client_host=request.client.host,
                request_id=get_request_id(),
                user_id=user_id,
                impersonator_user_id=impersonator_user_id,
                method=request.method,
                headers=repr(request.headers),
                url=request.url.path,
                query_params=repr(request.query_params),
                path_params=repr(request.path_params),
                body=str(body),
                process_time=process_time * 1000,
                status_code=response.status_code,
            )
            crud.audit.create(db=db, obj_in=audit_in)
            return response

        return custom_route_handler


class AuditorRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, route_class=AuditorRoute, **kwargs)
