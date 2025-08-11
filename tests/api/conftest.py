from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from kwik.api.api import api_router
from kwik.applications import Kwik

if TYPE_CHECKING:
    from collections.abc import Generator

    from kwik.core.settings import BaseKwikSettings


@pytest.fixture(scope="session")
def kwik_app(settings: BaseKwikSettings) -> Kwik:
    """Set up the Kwik application for testing."""
    return Kwik(settings, api_router)


@pytest.fixture
def client(kwik_app: Kwik) -> Generator[TestClient, None, None]:
    """Set up an HTTP client for testing."""
    fastapi_app = kwik_app._app
    with TestClient(app=fastapi_app) as client:
        yield client
