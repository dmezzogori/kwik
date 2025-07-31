"""Authentication token management for testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik import get_settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

Token = dict[str, str]


class TokensManager:
    """Manager for handling authentication tokens in test scenarios."""

    def __init__(self, client: TestClient) -> None:
        """Initialize tokens manager with test client."""
        self.client = client
        self._tokens: dict[str, Token] = {}

    def _get_token_headers(self, username: str, password: str) -> Token:
        login_data = {
            "username": username,
            "password": password,
        }
        r = self.client.post(f"{get_settings().API_V1_STR}/login/access-token", data=login_data)
        tokens = r.json()
        access_token = tokens["access_token"]
        return {"Authorization": f"Bearer {access_token}"}

    def _set_token_headers(self, *, token_name: str, username: str, password: str) -> Token:
        return self._tokens.setdefault(token_name, self._get_token_headers(username, password))
