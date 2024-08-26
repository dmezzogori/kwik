from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kwik.tests.client import TestClient


def test_docs(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
