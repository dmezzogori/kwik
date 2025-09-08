"""
Identity-Aware TestClient for enhanced authentication testing.

This module provides an enhanced TestClient that can easily switch between different
user contexts for testing authentication and authorization workflows.

Example usage:
    from kwik.testing import IdentityAwareTestClient
    from fastapi.testclient import TestClient

    # Wrap your FastAPI TestClient
    test_client = TestClient(app)
    client = IdentityAwareTestClient(test_client)

    # Make authenticated request as specific user
    response = client.get_as(user, "/protected-endpoint")

    # Switch context and make another request
    response = client.get_as(admin_user, "/admin-endpoint")

    # Make unauthenticated request
    response = client.get("/public-endpoint")
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from requests import Response

    from kwik.models import User
    from kwik.settings import BaseKwikSettings


class IdentityAwareTestClient:
    """
    Enhanced TestClient with built-in authentication context switching.

    Provides convenient methods for making authenticated requests as different users
    without manually managing authentication tokens or headers.
    """

    def __init__(self, client: TestClient, settings: BaseKwikSettings | None = None) -> None:
        """
        Initialize the identity-aware client.

        Args:
            client: Base TestClient instance to wrap
            settings: Optional settings for admin user detection

        """
        self._client = client
        self._token_cache: dict[int, str] = {}
        self._settings = settings

    def _get_auth_token(self, user: User) -> str:
        """
        Get authentication token for a user, caching for efficiency.

        Args:
            user: User to authenticate as

        Returns:
            Authentication token

        Raises:
            RuntimeError: If authentication fails

        """
        if user.id in self._token_cache:
            return self._token_cache[user.id]

        # Determine the correct password based on user email
        if user.email == "regular@example.com":
            password = "regularpassword123"  # noqa: S105
        elif self._settings and user.email == self._settings.FIRST_SUPERUSER:
            password = self._settings.FIRST_SUPERUSER_PASSWORD
        else:
            password = "testpassword123"  # Default test password  # noqa: S105

        response = self._client.post(
            "/api/v1/login/access-token",
            data={
                "username": user.email,
                "password": password,
            },
        )

        if response.status_code != HTTPStatus.OK:
            msg = f"Authentication failed for user {user.email}: {response.status_code} {response.text}"
            raise RuntimeError(msg)

        try:
            token = response.json()["access_token"]
        except (KeyError, ValueError) as e:
            msg = f"Invalid authentication response for user {user.email}: {e}"
            raise RuntimeError(msg) from e

        self._token_cache[user.id] = token
        return token

    def _make_authenticated_request(
        self,
        method: str,
        user: User,
        url: str,
        **kwargs,  # noqa: ANN003
    ) -> Response:
        """
        Make an authenticated request as a specific user.

        Args:
            method: HTTP method (GET, POST, etc.)
            user: User to authenticate as
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response object

        """
        token = self._get_auth_token(user)

        # Add authorization header, merging with any existing headers
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        return getattr(self._client, method.lower())(url, headers=headers, **kwargs)

    def get_as(self, user: User, url: str, **kwargs) -> Response:  # noqa: ANN003
        """
        Make authenticated GET request as specific user.

        Args:
            user: User to authenticate as
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response object

        Example:
            response = client.get_as(admin_user, "/admin/users")

        """
        return self._make_authenticated_request("GET", user, url, **kwargs)

    def post_as(self, user: User, url: str, **kwargs) -> Response:  # noqa: ANN003
        """
        Make authenticated POST request as specific user.

        Args:
            user: User to authenticate as
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response object

        Example:
            response = client.post_as(editor_user, "/posts", json={"title": "New Post"})

        """
        return self._make_authenticated_request("POST", user, url, **kwargs)

    def put_as(self, user: User, url: str, **kwargs) -> Response:  # noqa: ANN003
        """
        Make authenticated PUT request as specific user.

        Args:
            user: User to authenticate as
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response object

        """
        return self._make_authenticated_request("PUT", user, url, **kwargs)

    def patch_as(self, user: User, url: str, **kwargs) -> Response:  # noqa: ANN003
        """
        Make authenticated PATCH request as specific user.

        Args:
            user: User to authenticate as
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response object

        """
        return self._make_authenticated_request("PATCH", user, url, **kwargs)

    def delete_as(self, user: User, url: str, **kwargs) -> Response:  # noqa: ANN003
        """
        Make authenticated DELETE request as specific user.

        Args:
            user: User to authenticate as
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response object

        """
        return self._make_authenticated_request("DELETE", user, url, **kwargs)

    def clear_token_cache(self) -> None:
        """Clear the authentication token cache."""
        self._token_cache.clear()
