from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from kwik.tests.client import TestClient


@pytest.fixture(scope="function")
def msg() -> str:
    import random
    import string

    return "".join(random.choice(string.ascii_letters) for _ in range(10))


def test_get(client: TestClient, msg: str) -> None:
    response = client.get(f"http://localhost:8080/api/v1/tests/get/?msg={msg}")

    assert response.status_code == 200
    assert response.json() == {"msg": msg}


def test_post(client: TestClient, msg: str) -> None:
    response = client.post(f"http://localhost:8080/api/v1/tests/post/?msg={msg}")

    assert response.status_code == 200
    assert response.json() == {"msg": msg}


def test_put(client: TestClient, msg: str) -> None:
    response = client.put(f"http://localhost:8080/api/v1/tests/put/?msg={msg}")

    assert response.status_code == 200
    assert response.json() == {"msg": msg}


def test_delete(client: TestClient, msg: str) -> None:
    response = client.delete(f"http://localhost:8080/api/v1/tests/delete/?msg={msg}")

    assert response.status_code == 200
    assert response.json() == {"msg": msg}
