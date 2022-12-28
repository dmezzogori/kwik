from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import json
from functools import wraps

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from requests import Response


def assert_status_code_and_return_response(status_code: int):
    def wrapper(func: Callable[..., Response]) -> Callable:
        @wraps(func)
        def inner(*args, **kwargs) -> Any:
            response = func(*args, **kwargs)
            assert response.status_code == status_code
            return response.json()

        return inner

    return wrapper


class TestClientBase:
    """
    Base class for all test clients.
    """

    BASE_URI: str

    def __init__(self, client: TestClient, headers: dict[str, str]):
        self.client = client
        self.headers = headers

    @property
    def get_uri(self) -> str:
        return self.BASE_URI

    @property
    def get_multi_uri(self) -> str:
        return self.BASE_URI

    @property
    def post_uri(self) -> str:
        return self.BASE_URI

    @property
    def put_uri(self) -> str:
        return self.BASE_URI

    @property
    def delete_uri(self) -> str:
        return self.BASE_URI

    def make_post_data(self, **kwargs) -> Any:
        raise NotImplementedError

    def make_put_data(self, **kwargs) -> Any:
        raise NotImplementedError

    @assert_status_code_and_return_response(status_code=200)
    def get(self, id_: int) -> Response:
        return self.client.get(f"{self.get_uri}/{id_}", headers=self.headers)

    @assert_status_code_and_return_response(status_code=200)
    def get_multi(self) -> Response:
        return self.client.get(self.get_multi_uri, headers=self.headers)

    @assert_status_code_and_return_response(status_code=200)
    def post(self, data: Any) -> Response:
        json_compatible_data = jsonable_encoder(data)
        return self.client.post(f"{self.post_uri}/", data=json.dumps(json_compatible_data), headers=self.headers)

    @assert_status_code_and_return_response(status_code=200)
    def update(self, id_: int, data: Any) -> Response:
        json_compatible_data = jsonable_encoder(data)
        return self.client.put(
            f"{self.put_uri}/{id_}",
            data=json.dumps(json_compatible_data),
            headers=self.headers,
        )

    @assert_status_code_and_return_response(status_code=200)
    def delete(self, id_: int) -> Response:
        return self.client.delete(f"{self.delete_uri}/{id_}", headers=self.headers)
