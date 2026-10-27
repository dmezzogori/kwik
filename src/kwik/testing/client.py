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

import warnings
from http import HTTPStatus
from typing import TYPE_CHECKING

from kwik.auth import open_session
from kwik.security import create_token
from kwik.settings import BaseKwikSettings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from requests import Response

    from kwik.auth import AuthSessionStore
    from kwik.models import User


class IdentityAwareTestClient:
    """
    Enhanced TestClient with built-in authentication context switching.

    Provides convenient methods for making authenticated requests as different users
    without manually managing authentication tokens or headers. Tokens are minted
    directly from the application settings, so no request is spent on logging in.
    """

    def __init__(
        self,
        client: TestClient,
        settings: BaseKwikSettings | None = None,
        *,
        auth_session_store: AuthSessionStore | None = None,
    ) -> None:
        """
        Initialize the identity-aware client.

        Args:
            client: Base TestClient instance to wrap
            settings: Settings used to sign tokens; defaults to ``client.app.state.settings``,
                which the application lifespan sets
            auth_session_store: Store in which to open a session per user; defaults to the
                ``auth_session_store`` in ``client.app.state``, which ``Kwik`` sets

        """
        self._client = client
        self._token_cache: dict[int, str] = {}
        self._settings = settings
        self._auth_session_store = auth_session_store

    def _app_state_attribute(self, name: str) -> object | None:
        """Return ``client.app.state.<name>``, or None when the wrapped client has no such app state."""
        return getattr(getattr(getattr(self._client, "app", None), "state", None), name, None)

    def token_for(self, user: User) -> str:
        """
        Return a bearer token for ``user``, cached per user id.

        The token is signed with the settings (the ``settings`` argument, else the application's
        ``state.settings``). When the application has an auth session store the call opens a
        session in it, so the token passes the per-request session check. Only when no settings
        are available does it post the password form to ``/api/v1/login/access-token``, which is
        deprecated and removed in kwik 2.0.

        Args:
            user: User to authenticate as

        Returns:
            Access token

        Raises:
            RuntimeError: If the deprecated password form login fails

        """
        if user.id in self._token_cache:
            return self._token_cache[user.id]

        settings = self._settings
        if settings is None:
            candidate = self._app_state_attribute("settings")
            settings = candidate if isinstance(candidate, BaseKwikSettings) else None

        if settings is not None:
            store = self._auth_session_store or self._app_state_attribute("auth_session_store")
            if store is not None:
                token = open_session(user_id=user.id, settings=settings, store=store).access_token
            else:
                token = create_token(user_id=user.id, settings=settings).access_token
        else:
            warnings.warn(
                "IdentityAwareTestClient posts the password form because it has no settings: "
                "pass settings or run the app's lifespan; the password form fallback is removed in kwik 2.0",
                DeprecationWarning,
                stacklevel=2,
            )
            token = self._login_with_password_form(user)

        self._token_cache[user.id] = token
        return token

    def _get_auth_token(self, user: User) -> str:
        """Return a bearer token for ``user``; kept for callers of the pre-1.14 private name."""
        return self.token_for(user)

    def _login_with_password_form(self, user: User) -> str:
        """
        Obtain a token by guessing the user's password and posting the login form.

        Raises:
            RuntimeError: If authentication fails

        """
        # Determine the correct password based on user email
        is_regular = user.email == "regular@example.com"
        password = "regularpassword123" if is_regular else "testpassword123"

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
            return response.json()["access_token"]
        except (KeyError, ValueError) as e:
            msg = f"Invalid authentication response for user {user.email}: {e}"
            raise RuntimeError(msg) from e

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
