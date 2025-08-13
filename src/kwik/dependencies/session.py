"""
Kwik dependency injection for database sessions.

This module provides:
- Session: Annotated dependency type for injecting database sessions into Kwik endpoints
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as _Session

from kwik.database import session_scope


def _get_session(request: Request) -> Generator[_Session, None, None]:
    session: _Session = request.app.state.SessionLocal()
    with session_scope(session=session, commit=True) as session:
        yield session


Session = Annotated[_Session, Depends(_get_session)]

__all__ = ["Session"]
