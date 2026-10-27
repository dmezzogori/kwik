"""Tests for how IdentityAwareTestClient obtains the bearer token of a user."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from kwik.auth import InMemoryAuthSessionStore
from kwik.security import decode_token
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from kwik.models import User
    from kwik.settings import BaseKwikSettings

FORM_FALLBACK_WARNING = "password form fallback"


def _recording_client(captured: dict[str, str]) -> Mock:
    """Return a mocked TestClient whose login post records the submitted form and succeeds."""
    mock_response = Mock()
    mock_response.status_code = HTTPStatus.OK
    mock_response.json.return_value = {"access_token": "test_token", "token_type": "bearer"}

    def capture_post(*args, **kwargs) -> Mock:  # noqa: ANN002, ANN003, ARG001
        captured.update(kwargs.get("data", {}))
        return mock_response

    mock_client = Mock(spec=TestClient)
    mock_client.post = capture_post
    mock_client.get = Mock(return_value=Mock(status_code=HTTPStatus.OK))
    return mock_client


class TestTokenFor:
    """token_for mints tokens from settings instead of posting the password form."""

    def test_mints_token_from_settings_without_posting(self, settings: BaseKwikSettings, admin_user: User) -> None:
        """With settings the client never posts: it signs a token for the user id."""
        mock_client = Mock(spec=TestClient)
        mock_client.post = Mock(side_effect=AssertionError("must not post"))

        token = IdentityAwareTestClient(mock_client, settings).token_for(admin_user)

        payload = decode_token(token=token, settings=settings)
        assert payload.sub == admin_user.id
        assert payload.sid is None

    def test_opens_session_when_store_given(self, settings: BaseKwikSettings, admin_user: User) -> None:
        """With a store the token carries the id of a freshly opened session."""
        store = InMemoryAuthSessionStore()

        token = IdentityAwareTestClient(Mock(spec=TestClient), settings, auth_session_store=store).token_for(admin_user)

        record = store.get(decode_token(token=token, settings=settings).sid)
        assert record is not None
        assert record.user_id == admin_user.id

    def test_caches_per_user(self, settings: BaseKwikSettings, admin_user: User, regular_user: User) -> None:
        """A user gets one session; asking again returns the same token."""
        client = IdentityAwareTestClient(Mock(spec=TestClient), settings, auth_session_store=InMemoryAuthSessionStore())

        first = client.token_for(admin_user)

        assert client.token_for(admin_user) == first
        assert client.token_for(regular_user) != first

    def test_clear_token_cache_mints_a_new_token(self, settings: BaseKwikSettings, admin_user: User) -> None:
        """After clear_token_cache the next call opens a new session."""
        client = IdentityAwareTestClient(Mock(spec=TestClient), settings, auth_session_store=InMemoryAuthSessionStore())
        first = client.token_for(admin_user)

        client.clear_token_cache()

        assert client.token_for(admin_user) != first

    def test_get_auth_token_is_alias(self, settings: BaseKwikSettings, admin_user: User) -> None:
        """_get_auth_token (used by Teban) returns what token_for returns."""
        client = IdentityAwareTestClient(Mock(spec=TestClient), settings, auth_session_store=InMemoryAuthSessionStore())

        assert client._get_auth_token(admin_user) == client.token_for(admin_user)

    def test_get_auth_token_delegates_to_token_for(self, settings: BaseKwikSettings, admin_user: User) -> None:
        """A subclass overriding token_for also changes _get_auth_token."""
        sentinel = "overridden"

        class Custom(IdentityAwareTestClient):
            def token_for(self, user: User) -> str:  # noqa: ARG002
                return sentinel

        assert Custom(Mock(spec=TestClient), settings)._get_auth_token(admin_user) == sentinel

    def test_authenticated_request_uses_minted_token(self, settings: BaseKwikSettings, admin_user: User) -> None:
        """get_as sends the minted token as the bearer credential."""
        mock_client = Mock(spec=TestClient)
        client = IdentityAwareTestClient(mock_client, settings)

        client.get_as(admin_user, "/endpoint")

        headers = mock_client.get.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer {client.token_for(admin_user)}"


class TestPasswordFormFallback:
    """Without settings, the client falls back to the deprecated password form."""

    def test_fallback_posts_form_with_deprecation(self, mock_client: TestClient, test_user_for_testing: User) -> None:
        """No settings and no lifespan state: warn, then post the form."""
        with pytest.warns(DeprecationWarning, match=FORM_FALLBACK_WARNING):
            IdentityAwareTestClient(mock_client).get_as(test_user_for_testing, "/test-endpoint")

    def test_unrecognized_user_fallback_password(self, test_user_for_testing: User) -> None:
        """Users with an unrecognized email pattern get the default test password."""
        captured: dict[str, str] = {}
        identity_client = IdentityAwareTestClient(_recording_client(captured))

        with pytest.warns(DeprecationWarning, match=FORM_FALLBACK_WARNING):
            identity_client.get_as(test_user_for_testing, "/test-endpoint")

        assert captured["password"] == "testpassword123"
        assert captured["username"] == test_user_for_testing.email

    def test_regular_user_specific_password(self) -> None:
        """regular@example.com uses the specific regular password."""
        regular_user = Mock()
        regular_user.email = "regular@example.com"
        captured: dict[str, str] = {}
        identity_client = IdentityAwareTestClient(_recording_client(captured))

        with pytest.warns(DeprecationWarning, match=FORM_FALLBACK_WARNING):
            identity_client.get_as(regular_user, "/test-endpoint")

        assert captured["password"] == "regularpassword123"
        assert captured["username"] == "regular@example.com"
