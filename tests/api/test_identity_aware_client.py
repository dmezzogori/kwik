"""Tests for IdentityAwareTestClient against a running session-aware application."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from kwik.security import decode_token
from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from kwik.auth import InMemoryAuthSessionStore
    from kwik.models import User
    from kwik.settings import BaseKwikSettings


class TestIdentityAwareClientAppState:
    """The client reads what it needs from the application it wraps."""

    def test_reads_settings_and_store_from_app_state(
        self,
        client: TestClient,
        settings: BaseKwikSettings,
        auth_store: InMemoryAuthSessionStore,
        admin_user: User,
    ) -> None:
        """Given neither settings nor a store, the client uses the app's and opens a known session."""
        identity_client = IdentityAwareTestClient(client)

        token = identity_client.token_for(admin_user)

        session_id = decode_token(token=token, settings=settings).sid
        assert session_id is not None
        assert auth_store.get(session_id) is not None
        assert identity_client.get_as(admin_user, "/api/v1/users/me").status_code == HTTPStatus.OK
