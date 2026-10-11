"""Pool sizing and checkout timeout come from settings (teban #777)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from kwik.database import create_engine, warn_if_pool_exceeds_connections
from kwik.settings import BaseKwikSettings

if TYPE_CHECKING:
    from sqlalchemy.pool import QueuePool

POOL_SIZE = 3
MAX_OVERFLOW = 2
POOL_TIMEOUT = 0.2
TIMEOUT_CEILING = 2.0
MANY_WORKERS = 10
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 10.0


def test_pool_defaults() -> None:
    """Pool size and overflow keep their old values; the checkout timeout is 10 s."""
    settings = BaseKwikSettings()
    assert settings.POSTGRES_POOL_SIZE == DEFAULT_POOL_SIZE
    assert settings.POSTGRES_MAX_OVERFLOW == DEFAULT_MAX_OVERFLOW
    assert settings.POSTGRES_POOL_TIMEOUT == DEFAULT_POOL_TIMEOUT


def test_pool_timeout_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    """A zero checkout timeout is refused at startup."""
    monkeypatch.setenv("KWIK_POSTGRES_POOL_TIMEOUT", "0")
    with pytest.raises(ValidationError):
        BaseKwikSettings()


def test_engine_uses_configured_pool(settings: BaseKwikSettings) -> None:
    """The engine's pool reports the configured size, overflow and timeout."""
    configured = settings.model_copy(
        update={
            "POSTGRES_POOL_SIZE": POOL_SIZE,
            "POSTGRES_MAX_OVERFLOW": MAX_OVERFLOW,
            "POSTGRES_POOL_TIMEOUT": POOL_TIMEOUT,
        },
    )
    engine = create_engine(configured)
    pool: QueuePool = engine.pool  # type: ignore[assignment]
    try:
        assert pool.size() == POOL_SIZE
        assert pool._max_overflow == MAX_OVERFLOW
        assert pool._timeout == POOL_TIMEOUT
    finally:
        engine.dispose()


def test_starved_checkout_fails_fast(settings: BaseKwikSettings) -> None:
    """With the pool exhausted, a checkout fails after the configured timeout, not 30 s."""
    configured = settings.model_copy(
        update={"POSTGRES_POOL_SIZE": 1, "POSTGRES_MAX_OVERFLOW": 0, "POSTGRES_POOL_TIMEOUT": POOL_TIMEOUT},
    )
    engine = create_engine(configured)
    held = engine.connect()
    try:
        started = time.monotonic()
        with pytest.raises(PoolTimeoutError):
            engine.connect()
        assert time.monotonic() - started < TIMEOUT_CEILING
    finally:
        held.close()
        engine.dispose()


def test_warns_when_pools_exceed_max_connections(settings: BaseKwikSettings) -> None:
    """Workers x (size + overflow) above the server's connection limit is logged."""
    configured = settings.model_copy(update={"BACKEND_WORKERS": MANY_WORKERS})
    with patch("kwik.database.logger") as logger:
        assert warn_if_pool_exceeds_connections(configured) is True
    logger.warning.assert_called_once()


def test_no_warning_within_limit(settings: BaseKwikSettings) -> None:
    """The default single worker fits the default connection limit."""
    with patch("kwik.database.logger") as logger:
        assert warn_if_pool_exceeds_connections(settings) is False
    logger.warning.assert_not_called()
