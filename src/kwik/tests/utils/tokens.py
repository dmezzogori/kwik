from __future__ import annotations

from fastapi.testclient import TestClient

import kwik

Token = dict[str, str]


class TokensManager:
    """Manager for handling authentication tokens in test scenarios."""

    def __init__(self, client: TestClient):
        """Initialize tokens manager with test client."""
        self.client = client
        self._tokens: dict[str, Token] = {}

    def _get_token_headers(self, username: str, password: str) -> Token:
        login_data = {
            "username": username,
            "password": password,
        }
        r = self.client.post(f"{kwik.settings.API_V1_STR}/login/access-token", data=login_data)
        tokens = r.json()
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        return headers

    def _set_token_headers(self, *, token_name: str, username: str, password: str) -> Token:
        return self._tokens.setdefault(token_name, self._get_token_headers(username, password))
