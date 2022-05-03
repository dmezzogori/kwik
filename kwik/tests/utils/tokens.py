from typing import Dict

import kwik
from fastapi.testclient import TestClient

Token = Dict[str, str]


def get_token_headers(username: str, password: str, client: TestClient) -> Token:
    login_data = {
        "username": username,
        "password": password,
    }
    r = client.post(f"{kwik.settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers
