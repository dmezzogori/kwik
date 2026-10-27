"""Prove kwik commits the request session before the response is sent (teban #823)."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as OrmSession

from kwik.applications import Kwik
from kwik.database import create_session
from kwik.dependencies import Session  # noqa: TC001 - FastAPI resolves endpoint annotations at runtime
from kwik.dependencies.session import _commit_session, _get_session
from kwik.exceptions import InvalidBearerTokenError, SessionRevokedError
from kwik.models import Role

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from sqlalchemy import Engine
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from kwik.models import User
    from kwik.settings import BaseKwikSettings

PROBE_PATH = "/probe"


def _recording(app: ASGIApp, events: list[str], on_start: Callable[[], None] | None = None) -> ASGIApp:
    """Wrap an ASGI app, appending "response.start" when the status line goes out."""

    async def wrapped(scope: Scope, receive: Receive, send: Send) -> None:
        async def recording_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                if on_start is not None:
                    on_start()
                events.append("response.start")
            await send(message)

        await app(scope, receive, recording_send)

    return wrapped


def _role_exists(engine: Engine, name: str) -> bool:
    """Read from a connection of its own, so only committed rows are visible."""
    with create_session(engine=engine) as other:
        return other.scalar(select(Role).where(Role.name == name)) is not None


def _delete_role(engine: Engine, name: str) -> None:
    """Remove a probe role that a test committed for real."""
    with create_session(engine=engine) as cleanup:
        cleanup.execute(delete(Role).where(Role.name == name))
        cleanup.commit()


def _fake_session_override(fake: MagicMock) -> Callable[[], Iterator[OrmSession]]:
    """Build a ``_get_session`` override yielding ``fake``."""

    def override() -> Iterator[OrmSession]:
        yield fake

    return override


def test_commit_happens_before_response_start(settings: BaseKwikSettings) -> None:
    """The session's commit is recorded before the status line is sent."""
    events: list[str] = []
    router = APIRouter()

    @router.get(PROBE_PATH)
    def probe(session: Session) -> dict[str, bool]:  # noqa: ARG001
        return {"ok": True}

    kwik = Kwik(settings=settings, api_router=router)
    fake = MagicMock(spec=OrmSession)
    fake.commit.side_effect = lambda: events.append("commit")
    kwik.app.dependency_overrides[_get_session] = _fake_session_override(fake)

    with TestClient(_recording(kwik.app, events)) as client:
        assert client.get(f"{settings.API_V1_STR}{PROBE_PATH}").status_code == HTTPStatus.OK
    assert events == ["commit", "response.start"]


def test_write_visible_to_other_connection_at_response_start(
    settings: BaseKwikSettings, engine: Engine, admin_user: User
) -> None:
    """A row written by the route is readable from another connection when the response starts."""
    name = "commit-probe-visible"
    seen: list[bool] = []
    router = APIRouter()

    @router.post(PROBE_PATH)
    def probe(session: Session) -> dict[str, bool]:
        session.add(Role(name=name, is_active=True, creator_user_id=admin_user.id))
        return {"ok": True}

    kwik = Kwik(settings=settings, api_router=router)
    try:
        with TestClient(_recording(kwik.app, [], on_start=lambda: seen.append(_role_exists(engine, name)))) as client:
            assert client.post(f"{settings.API_V1_STR}{PROBE_PATH}").status_code == HTTPStatus.OK
        assert seen == [True]
    finally:
        _delete_role(engine, name)


def test_raise_after_write_rolls_back(settings: BaseKwikSettings, engine: Engine, admin_user: User) -> None:
    """A route that writes and then raises commits nothing."""
    name = "commit-probe-raise"
    router = APIRouter()

    @router.post(PROBE_PATH)
    def probe(session: Session) -> None:
        session.add(Role(name=name, is_active=True, creator_user_id=admin_user.id))
        session.flush()
        raise HTTPException(status_code=HTTPStatus.CONFLICT)

    kwik = Kwik(settings=settings, api_router=router)
    try:
        with TestClient(kwik.app) as client:
            assert client.post(f"{settings.API_V1_STR}{PROBE_PATH}").status_code == HTTPStatus.CONFLICT
        assert _role_exists(engine, name) is False
    finally:
        _delete_role(engine, name)


def test_streaming_write_committed_by_teardown(settings: BaseKwikSettings, engine: Engine, admin_user: User) -> None:
    """Writes made while streaming the body, after the endpoint returned, are still committed."""
    name = "commit-probe-stream"
    router = APIRouter()

    @router.get(PROBE_PATH)
    def probe(session: Session) -> StreamingResponse:
        def body() -> Iterator[bytes]:
            session.add(Role(name=name, is_active=True, creator_user_id=admin_user.id))
            yield b"x"

        return StreamingResponse(body())

    kwik = Kwik(settings=settings, api_router=router)
    try:
        with TestClient(kwik.app) as client:
            assert client.get(f"{settings.API_V1_STR}{PROBE_PATH}").content == b"x"
        assert _role_exists(engine, name) is True
    finally:
        _delete_role(engine, name)


def test_commit_failure_is_server_error(settings: BaseKwikSettings) -> None:
    """A failing commit yields a 500 rather than a success sent before the failure."""
    router = APIRouter()

    @router.get(PROBE_PATH)
    def probe(session: Session) -> dict[str, bool]:  # noqa: ARG001
        return {"ok": True}

    kwik = Kwik(settings=settings, api_router=router)
    fake = MagicMock(spec=OrmSession)
    fake.commit.side_effect = RuntimeError("commit failed")
    kwik.app.dependency_overrides[_get_session] = _fake_session_override(fake)

    with TestClient(kwik.app, raise_server_exceptions=False) as client:
        assert client.get(f"{settings.API_V1_STR}{PROBE_PATH}").status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_dependency_installed_app_wide(settings: BaseKwikSettings) -> None:
    """Every Kwik app carries the function-scoped commit dependency."""
    kwik = Kwik(settings=settings, api_router=APIRouter())
    assert any(
        dependency.dependency is _commit_session and dependency.scope == "function"
        for dependency in kwik.app.router.dependencies
    )


def _throw_into_commit(session: MagicMock, error: Exception) -> None:
    """Drive ``_commit_session`` by hand as FastAPI does when the endpoint raised ``error``."""
    teardown = _commit_session(session)
    next(teardown)
    teardown.throw(error)


def test_normal_return_commits_once() -> None:
    """An endpoint that returns gets exactly one commit."""
    session = MagicMock(spec=OrmSession)
    teardown = _commit_session(session)
    next(teardown)
    with pytest.raises(StopIteration):
        next(teardown)
    session.commit.assert_called_once_with()


def test_session_revoked_error_commits_and_reraises_unchanged() -> None:
    """A SessionRevokedError commits the session once and then propagates as the same object."""
    session = MagicMock(spec=OrmSession)
    error = SessionRevokedError(detail="Refresh token reused; session revoked")
    with pytest.raises(SessionRevokedError) as raised:
        _throw_into_commit(session, error)
    assert raised.value is error
    session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "error",
    [InvalidBearerTokenError(), HTTPException(status_code=HTTPStatus.CONFLICT), RuntimeError("boom")],
    ids=["invalid-bearer-token", "http-exception", "runtime-error"],
)
def test_other_errors_pass_through_without_commit(error: Exception) -> None:
    """Every exception other than SessionRevokedError, its base class included, commits nothing."""
    session = MagicMock(spec=OrmSession)
    with pytest.raises(type(error)) as raised:
        _throw_into_commit(session, error)
    assert raised.value is error
    session.commit.assert_not_called()


def test_failed_commit_after_session_revoked_error_propagates() -> None:
    """If committing the revocation fails, the commit error propagates instead of being swallowed."""
    session = MagicMock(spec=OrmSession)
    commit_error = RuntimeError("commit failed")
    session.commit.side_effect = commit_error
    revoked = SessionRevokedError()
    with pytest.raises(RuntimeError) as raised:
        _throw_into_commit(session, revoked)
    assert raised.value is commit_error
    assert raised.value.__context__ is revoked
