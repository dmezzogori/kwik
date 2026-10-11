"""Uvicorn's graceful shutdown must end before gunicorn kills the worker (teban #757)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from gunicorn.config import Config
from gunicorn.glogging import Logger

from kwik.applications.run import run
from kwik.applications.uvicorn import GRACEFUL_SHUTDOWN_MARGIN, KwikUvicornWorker

if TYPE_CHECKING:
    import pytest

GUNICORN_GRACEFUL = 30
SHORT_GRACEFUL = 3
CONFIGURED_GRACEFUL = 45


def _worker(graceful_timeout: int) -> KwikUvicornWorker:
    """Build a worker the way gunicorn's arbiter does, with the given graceful timeout."""
    cfg = Config()
    cfg.set("graceful_timeout", graceful_timeout)
    return KwikUvicornWorker(
        age=0,
        ppid=os.getpid(),
        sockets=[],
        app=MagicMock(),
        timeout=GUNICORN_GRACEFUL,
        cfg=cfg,
        log=Logger(cfg),
    )


def test_shutdown_timeout_is_graceful_timeout_minus_margin() -> None:
    """The worker leaves a margin below gunicorn's graceful timeout."""
    worker = _worker(GUNICORN_GRACEFUL)
    assert worker.config.timeout_graceful_shutdown == GUNICORN_GRACEFUL - GRACEFUL_SHUTDOWN_MARGIN


def test_shutdown_timeout_never_below_one_second() -> None:
    """A graceful timeout smaller than the margin still yields a positive timeout."""
    assert _worker(SHORT_GRACEFUL).config.timeout_graceful_shutdown == 1


def test_run_passes_graceful_timeout_to_gunicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production mode hands BACKEND_GRACEFUL_TIMEOUT to gunicorn."""
    monkeypatch.setenv("KWIK_APP_ENV", "production")
    monkeypatch.setenv("KWIK_BACKEND_GRACEFUL_TIMEOUT", str(CONFIGURED_GRACEFUL))
    with patch("kwik.applications.run.KwikGunicornApplication") as application:
        run("myproject.main")
    options = application.call_args.args[1]
    assert options["graceful_timeout"] == CONFIGURED_GRACEFUL
