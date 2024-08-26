from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def app():
    import os

    os.environ["TEST_ENV"] = "True"

    import kwik
    from kwik.api.api import api_router

    k = kwik.Kwik(api_router)
    return k._app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c
