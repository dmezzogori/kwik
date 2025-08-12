"""
Test module for kwik API endpoints.

This module contains test cases for various API endpoints including:
- Context router endpoints (settings, session)
- Authentication functionality and fixtures
"""

from http import HTTPStatus

from fastapi.testclient import TestClient

from kwik.models import User
from kwik.settings import BaseKwikSettings


class TestContextRouter:
    """
    Test cases for the context router API endpoints.

    This class contains tests for the context-related API endpoints,
    including settings and session management functionality.
    """

    def test_get_settings(self, client: TestClient, settings: BaseKwikSettings) -> None:
        """
        Test the settings endpoint returns correct configuration values.

        Parameters
        ----------
        client : TestClient
            The FastAPI test client for making HTTP requests.
        settings : BaseKwikSettings
            The application settings configuration object.

        """
        response = client.get("/api/v1/context/settings")

        status_code = response.status_code
        json_response = response.json()

        assert status_code == HTTPStatus.OK
        assert json_response["POSTGRES_SERVER"] == settings.POSTGRES_SERVER
        assert json_response["POSTGRES_PORT"] == settings.POSTGRES_PORT
        assert json_response["POSTGRES_DB"] == settings.POSTGRES_DB
        assert json_response["POSTGRES_USER"] == settings.POSTGRES_USER
        assert json_response["POSTGRES_PASSWORD"] == settings.POSTGRES_PASSWORD

    def test_get_session(self, client: TestClient) -> None:
        """
        Test the session endpoint returns correct response and increments db_rows.

        Parameters
        ----------
        client : TestClient
            The FastAPI test client for making HTTP requests.

        """
        response = client.get("/api/v1/context/session")

        status_code = response.status_code
        json_response = response.json()

        assert status_code == HTTPStatus.OK
        assert json_response["ok"] is True
        assert json_response["db_rows"] == 1

        response = client.get("/api/v1/context/session")

        status_code = response.status_code
        json_response = response.json()

        assert status_code == HTTPStatus.OK
        assert json_response["ok"] is True

        expected_db_rows = 2
        assert json_response["db_rows"] == expected_db_rows


class TestAuthenticationFixtures:
    """Example tests demonstrating the new authentication fixtures."""

    def test_authenticated_client_has_headers(self, authenticated_client: TestClient) -> None:
        """Test that authenticated client has Authorization header set."""
        assert "Authorization" in authenticated_client.headers
        assert authenticated_client.headers["Authorization"].startswith("Bearer ")

    def test_login_endpoint_with_admin_credentials(
        self, client: TestClient, admin_user: User, settings: BaseKwikSettings
    ) -> None:
        """Test login endpoint works with admin user credentials."""
        response = client.post(
            "/api/v1/login/access-token",
            data={
                "username": admin_user.email,
                "password": settings.FIRST_SUPERUSER_PASSWORD,
            },
        )

        assert response.status_code == HTTPStatus.OK
        json_response = response.json()
        assert "access_token" in json_response
        assert json_response["token_type"] == "bearer"
