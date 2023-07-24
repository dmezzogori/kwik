from __future__ import annotations

import urllib.parse
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from pydantic import BaseModel

if TYPE_CHECKING:
    from httpx import Response


ResponseSchema = TypeVar("ResponseSchema", bound=BaseModel)

EndpointReturn = Mapping[str, Any] | list[Mapping[str, Any]]


def assert_status_code_and_return_response(response: Response, status_code: int = 200) -> EndpointReturn:
    assert response.status_code == status_code, response.text
    return response.json()


class TestClientBase:
    """
    Base class for all test clients.
    """

    BASE_URI: str

    def __init__(self, client: TestClient, headers: dict[str, str]) -> None:
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
        return f"{self.BASE_URI}/"

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

    def get(self, id_: int, status_code: int = 200) -> EndpointReturn | None:
        return assert_status_code_and_return_response(
            self.client.get(f"{self.get_uri}/{id_}", headers=self.headers), status_code=status_code
        )

    def get_multi(
        self,
        filters: dict[str, str] | None = None,
        sorting: tuple[str, Literal["asc", "desc"]] | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> EndpointReturn:
        exclude_keys = {
            "creation_time",
            "last_modification_time",
            "creator_user_id",
            "last_modifier_user_id",
        }

        query = {"skip": skip, "limit": limit}
        if filters is not None:
            query.update(filters)
        if sorting is not None:
            query["sorting"] = f"{sorting[0]}:{sorting[1]}"
        query_string = urllib.parse.urlencode(
            query={k: v for k, v in query.items() if v is not None and k not in exclude_keys}
        )
        if query_string:
            uri = f"{self.get_multi_uri}/?{query_string}"
        else:
            uri = self.get_multi_uri

        return assert_status_code_and_return_response(self.client.get(uri, headers=self.headers))

    def post(self, data: BaseModel, status_code: int = 200, post_uri: str | None = None) -> EndpointReturn:
        if post_uri is None:
            post_uri = self.post_uri

        return assert_status_code_and_return_response(
            self.client.post(f"{post_uri or self.post_uri}", json=jsonable_encoder(data), headers=self.headers),
            status_code=status_code,
        )

    def update(self, id_: int, data: BaseModel, put_uri: str | None = None) -> EndpointReturn:
        put_uri = put_uri or f"{self.put_uri}/{id_}"
        return assert_status_code_and_return_response(
            self.client.put(
                put_uri,
                json=jsonable_encoder(data),
                headers=self.headers,
            )
        )

    def delete(self, id_: int) -> EndpointReturn:
        return assert_status_code_and_return_response(
            self.client.delete(f"{self.delete_uri}/{id_}", headers=self.headers)
        )
