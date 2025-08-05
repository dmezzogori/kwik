"""Database session management utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request
    from sqlalchemy.orm import Session


def get_db_from_request(request: Request) -> Session:
    """Get the session instance attached to a Kwik request."""
    return request.state.db
