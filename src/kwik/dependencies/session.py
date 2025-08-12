"""
Kwik dependency injection for database sessions.

This module provides:
- Session: Annotated dependency type for injecting database sessions into Kwik endpoints
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as _Session

from kwik.logging import logger


def _get_session(request: Request) -> Generator[_Session, None, None]:
    session: _Session = request.app.state.SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.exception(f"Error occurred while processing request: {e}")
        session.rollback()
        raise
    finally:
        session.close()


Session = Annotated[_Session, Depends(_get_session)]

__all__ = ["Session"]
