from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

db_conn_ctx_var: ContextVar[Session | None] = ContextVar("db_conn_ctx_var", default=None)
