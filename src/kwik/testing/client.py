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

from typing import TYPE_CHECKING, Any

from fastapi import status

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from requests import Response

    from kwik.models import User


class IdentityAwareTestClient:
    """
    Enhanced TestClient with built-in authentication context switching.

    Provides convenient methods for making authenticated requests as different users
    without manually managing authentication tokens or headers.
    """

    def __init__(self, client: TestClient) -> None:
        """
        Initialize the identity-aware client.

        Args:
            client: Base TestClient instance to wrap

        """
        self._client = client
        self._token_cache: dict[int, str] = {}

    def _get_auth_token(self, user: User) -> str:
        """
        Get authentication token for a user, caching for efficiency.

        Args:
            user: User to authenticate as

        Returns:
            Authentication token

        Raises:
            AssertionError: If authentication fails

        """
        if user.id in self._token_cache:
            return self._token_cache[user.id]

        response = self._client.post(
            "/api/v1/login/access-token",
            data={
                "username": user.email,
                "password": "testpassword123",  # Default test password
            },
        )

        assert response.status_code == status.HTTP_200_OK, (
            f"Authentication failed for user {user.email}: {response.text}"
        )

        token = response.json()["access_token"]
        self._token_cache[user.id] = token
        return token

    def _make_authenticated_request(
        self,
        method: str,
        user: User,
        url: str,
        **kwargs: Any,
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

        # Add authorization header
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers

        return getattr(self._client, method.lower())(url, **kwargs)

    def get_as(self, user: User, url: str, **kwargs: Any) -> Response:
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

    def post_as(self, user: User, url: str, **kwargs: Any) -> Response:
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

    def put_as(self, user: User, url: str, **kwargs: Any) -> Response:
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

    def patch_as(self, user: User, url: str, **kwargs: Any) -> Response:
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

    def delete_as(self, user: User, url: str, **kwargs: Any) -> Response:
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

    # Delegate all other methods to the underlying client
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown methods to the underlying TestClient."""
        return getattr(self._client, name)
