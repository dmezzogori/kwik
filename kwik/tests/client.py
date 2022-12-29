from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, TypeVar, Generic, get_args

from fastapi.testclient import TestClient
from pydantic import BaseModel

if TYPE_CHECKING:
    from httpx import Response


GetSchema = TypeVar("GetSchema", bound=BaseModel)
PostSchema = TypeVar("PostSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
DeleteSchema = TypeVar("DeleteSchema", bound=BaseModel)


def assert_status_code_and_return_response(
    response: Response, status_code: int = 200
) -> Mapping[str, Any] | list[Mapping[str, Any]]:
    assert response.status_code == status_code
    return response.json()


class TestClientBase(Generic[GetSchema, PostSchema, UpdateSchema, DeleteSchema]):
    """
    Base class for all test clients.
    """

    BASE_URI: str

    def __init__(self, client: TestClient, headers: dict[str, str]) -> None:
        self.client = client
        self.headers = headers
        self.get_schema, self.post_schema, self.update_schema, self.delete_schema = get_args(self.__orig_bases__[0])

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

    def make_post_data(self, **kwargs):
        raise NotImplementedError

    def make_put_data(self, **kwargs):
        raise NotImplementedError

    def get(self, id_: int) -> GetSchema:
        return self.get_schema(
            **assert_status_code_and_return_response(self.client.get(f"{self.get_uri}/{id_}", headers=self.headers))
        )

    def get_multi(self) -> list[GetSchema]:
        return [
            self.get_schema(**item)
            for item in assert_status_code_and_return_response(
                self.client.get(self.get_multi_uri, headers=self.headers)
            )["data"]
        ]

    def post(self, data: BaseModel) -> PostSchema:
        return self.post_schema(
            **assert_status_code_and_return_response(
                self.client.post(f"{self.post_uri}/", json=data.dict(), headers=self.headers)
            )
        )

    def update(self, id_: int, data: BaseModel) -> UpdateSchema:
        return self.update_schema(
            **assert_status_code_and_return_response(
                self.client.put(
                    f"{self.put_uri}/{id_}",
                    json=data.dict(),
                    headers=self.headers,
                )
            )
        )

    def delete(self, id_: int) -> DeleteSchema:
        return self.delete_schema(
            **assert_status_code_and_return_response(
                self.client.delete(f"{self.delete_uri}/{id_}", headers=self.headers)
            )
        )
