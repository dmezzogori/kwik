import time
from typing import Callable

import kwik
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
from jose import jwt
from kwik import crud, schemas
from kwik.api.deps import get_current_user, current_token, get_token
from kwik.core import security
from kwik.middlewares import get_request_id


class KwikRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            # noinspection PyAttributeOutsideInit
            self._body = body
        return self._body

    @property
    def token(self) -> str | None:
        auth = self.headers.get("Authorization")
        if auth is not None and "Bearer " in auth:
            return auth.replace("Bearer ", "")
        return None


class AuditedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            from kwik.database.db_context_var import current_user_ctx_var

            # start the timer
            start = time.time()

            # override the request object
            request = KwikRequest(request.scope, request.receive)
            body = await request.body()

            # we set the current user in the context variable
            user_ctx_token = None
            user_id = None
            impersonator_user_id = None
            if request.token is not None:
                user = get_current_user(token=get_token(request.token))
                user_ctx_token = current_user_ctx_var.set(user)
                user_id = user.id

                payload = jwt.decode(request.token, kwik.settings.SECRET_KEY, algorithms=[security.ALGORITHM])
                token_data = schemas.TokenPayload(**payload)

                if token_data.kwik_impersonate != "":
                    impersonator_user_id = int(token_data.kwik_impersonate)

            # let's process the request
            response: Response = await original_route_handler(request)

            # as soon as the response is ready, we can reset the user context variable
            if user_ctx_token is not None:
                current_user_ctx_var.reset(user_ctx_token)

            # we stop the timer
            process_time = time.time() - start
            response.headers["X-Response-Time"] = str(process_time)

            # let's audit the request
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
                process_time=process_time * 1_000,
                status_code=response.status_code,
            )
            crud.audit.create(obj_in=audit_in)
            return response

        return custom_route_handler


class AuditorRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("dependencies", []).append(current_token)
        super().__init__(*args, route_class=AuditedRoute, **kwargs)
