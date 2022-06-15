from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kwik import models
    from .session import KwikSession

db_conn_ctx_var: ContextVar[KwikSession | None] = ContextVar("db_conn_ctx_var", default=None)
current_user_ctx_var: ContextVar[models.User | None] = ContextVar("current_user_ctx_var", default=None)
