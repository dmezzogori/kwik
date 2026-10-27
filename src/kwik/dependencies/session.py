"""
Kwik dependency injection for database sessions.

This module provides:
- Session: Annotated dependency type for injecting database sessions into Kwik endpoints
- _commit_session: the function-scoped dependency ``Kwik`` installs app-wide so writes
  are committed before the response is sent
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as _Session

from kwik.database import session_scope
from kwik.exceptions.auth import SessionRevokedError


def _get_session(request: Request) -> Generator[_Session, None, None]:
    """
    Yield the request's session, owning its whole lifecycle.

    Request-scoped: it closes after the response was sent. On the way out it rolls
    back on error and otherwise commits whatever ``_commit_session`` did not see
    (writes made while streaming a body or in background tasks).
    """
    session: _Session = request.app.state.SessionLocal()
    with session_scope(session=session, commit=True) as session:
        yield session


def _commit_session(session: Annotated[_Session, Depends(_get_session)]) -> Generator[None, None, None]:
    """
    Commit the request's session once the endpoint returns, before the response is sent.

    Installed app-wide by ``Kwik`` with ``scope="function"``: FastAPI closes
    function-scoped dependencies after the endpoint ran and its response was
    serialized, but before the status line goes out, so a client that acts on
    the response at once finds the write committed. It shares the request's
    cached session; ``_get_session`` still owns the session and closes it after
    the response.

    If the endpoint raised, the exception passes through this generator before
    the commit line and nothing is committed. If the commit fails, the client
    gets a server error instead of a success sent before the failure.

    The one exception is ``SessionRevokedError``: ``refresh_session`` raises it
    right after ``store.revoke(...)``, and a store bound to the request's session
    wrote the revocation into it. That error commits the session and is then
    re-raised unchanged, so the client still gets the 401 and the revocation is
    kept. Everything pending in the session is committed with it: on kwik's
    ``POST /login/refresh`` the store's own writes are the only ones, but an
    application route that writes other data and then calls ``refresh_session``
    has those writes committed too. If that commit fails, its error propagates
    and the client gets a server error.
    """
    try:
        yield
    except SessionRevokedError:
        session.commit()
        raise
    session.commit()


Session = Annotated[_Session, Depends(_get_session)]

__all__ = ["Session"]
