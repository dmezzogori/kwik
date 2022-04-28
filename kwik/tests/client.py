import json
from functools import wraps
from typing import Any, Callable

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from requests import Response


def assert_status_code_and_return_response(func: Callable[..., Response]) -> Callable:
    @wraps(func)
    def inner(*args, status_code: int, **kwargs) -> Any:
        response = func(*args, **kwargs)
        assert response.status_code == status_code
        return response.json()

    return inner


class TestClientBase:
    """
    Base class for all test clients.
    """

    BASE_URI: str

    def __init__(self, client: TestClient):
        self.client = client

    @property
    def get_uri(self) -> str:
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

    @assert_status_code_and_return_response
    def get_multi(self, headers: dict[str, str], status_code=200) -> Response:
        return self.client.get(self.get_uri, headers=headers)

    @assert_status_code_and_return_response
    def get_single(self, id_: int, headers: dict[str, str], status_code=200) -> Response:
        return self.client.get(f"{self.get_uri}/{id_}", headers=headers)

    @assert_status_code_and_return_response
    def post(self, data: Any, headers: dict[str, str], status_code=200) -> Response:
        json_compatible_data = jsonable_encoder(data)
        return self.client.post(f"{self.post_uri}/", data=json.dumps(json_compatible_data), headers=headers)

    @assert_status_code_and_return_response
    def update(self, id_: int, data: Any, headers: dict[str, str], status_code=200) -> Response:
        json_compatible_data = jsonable_encoder(data)
        return self.client.put(f"{self.put_uri}/{id_}", data=json.dumps(json_compatible_data), headers=headers)

    @assert_status_code_and_return_response
    def delete(self, id_: int, headers: dict[str, str], status_code=200) -> Response:
        return self.client.delete(f"{self.delete_uri}/{id_}", headers=headers)
