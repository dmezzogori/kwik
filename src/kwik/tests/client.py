"""Enhanced test client for API testing."""

from __future__ import annotations

import urllib.parse
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, Never

from fastapi.encoders import jsonable_encoder

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx import Response
    from pydantic import BaseModel


EndpointReturn = Mapping[str, Any] | list[Mapping[str, Any]]


def assert_status_code_and_return_response(response: Response, status_code: int = 200) -> EndpointReturn:
    """Assert HTTP response status code and return JSON response data."""
    assert response.status_code == status_code, response.text
    return response.json()


class TestClientBase:
    """Base class for all test clients."""

    BASE_URI: str

    def __init__(self, client: TestClient, headers: dict[str, str]) -> None:
        """Initialize test client with HTTP client and request headers."""
        self.client = client
        self.headers = headers

    @property
    def get_uri(self) -> str:
        """Get URI for single resource retrieval."""
        return self.BASE_URI

    @property
    def get_multi_uri(self) -> str:
        """Get URI for multiple resource retrieval."""
        return self.BASE_URI

    @property
    def post_uri(self) -> str:
        """Get URI for resource creation."""
        return f"{self.BASE_URI}/"

    @property
    def put_uri(self) -> str:
        """Get URI for resource updates."""
        return self.BASE_URI

    @property
    def delete_uri(self) -> str:
        """Get URI for resource deletion."""
        return self.BASE_URI

    def make_post_data(self, **kwargs: Any) -> Never:  # noqa: ANN401
        """Create data for POST requests - must be implemented by subclasses."""
        raise NotImplementedError

    def make_put_data(self, **kwargs: Any) -> Never:  # noqa: ANN401
        """Create data for PUT requests - must be implemented by subclasses."""
        raise NotImplementedError

    def get(self, id_: int, status_code: int = 200) -> EndpointReturn | None:
        """Get single resource by ID."""
        return assert_status_code_and_return_response(
            self.client.get(f"{self.get_uri}/{id_}", headers=self.headers),
            status_code=status_code,
        )

    def get_multi(
        self,
        filters: dict[str, str] | None = None,
        sorting: tuple[str, Literal["asc", "desc"]] | None = None,
        skip: int | None = None,
        limit: int | None = None,
    ) -> EndpointReturn:
        """Get multiple resources with optional filtering, sorting, and pagination."""
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
            query={k: v for k, v in query.items() if v is not None and k not in exclude_keys},
        )
        uri = f"{self.get_multi_uri}/?{query_string}" if query_string else self.get_multi_uri

        return assert_status_code_and_return_response(self.client.get(uri, headers=self.headers))

    def post(self, data: BaseModel, status_code: int = 200, post_uri: str | None = None) -> EndpointReturn:
        """Create new resource via POST request."""
        if post_uri is None:
            post_uri = self.post_uri

        return assert_status_code_and_return_response(
            self.client.post(f"{post_uri or self.post_uri}", json=jsonable_encoder(data), headers=self.headers),
            status_code=status_code,
        )

    def update(self, id_: int, data: BaseModel, put_uri: str | None = None) -> EndpointReturn:
        """Update existing resource via PUT request."""
        put_uri = put_uri or f"{self.put_uri}/{id_}"
        return assert_status_code_and_return_response(
            self.client.put(
                put_uri,
                json=jsonable_encoder(data),
                headers=self.headers,
            ),
        )

    def delete(self, id_: int) -> EndpointReturn:
        """Delete resource by ID via DELETE request."""
        return assert_status_code_and_return_response(
            self.client.delete(f"{self.delete_uri}/{id_}", headers=self.headers),
        )
