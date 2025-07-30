from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

REQUEST_ID_CTX_KEY = "request_id"

_request_id_ctx_var: ContextVar[str | None] = ContextVar(
    REQUEST_ID_CTX_KEY, default=None,
)


def get_request_id() -> str:
    """Get current request ID from context variable."""
    return _request_id_ctx_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware for setting unique request IDs in context variables."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        """Set unique request ID in context for request lifetime."""
        token = _request_id_ctx_var.set(str(uuid4()))
        response = await call_next(request)
        _request_id_ctx_var.reset(token)
        return response
