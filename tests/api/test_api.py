from http import HTTPStatus

from fastapi.testclient import TestClient

from kwik.core.settings import BaseKwikSettings
from kwik.models import User


class TestContextRouter:
    def test_get_settings(self, client: TestClient, settings: BaseKwikSettings) -> None:
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
        assert json_response["db_rows"] == 2


class TestAuthenticationFixtures:
    """Example tests demonstrating the new authentication fixtures."""

    def test_admin_user_created(self, admin_user: User) -> None:
        """Test that admin user fixture creates a user with correct properties."""
        assert admin_user.email == "admin@example.com"
        assert admin_user.name == "admin"
        assert admin_user.surname == "admin"
        assert admin_user.is_active is True

    def test_admin_token_obtained(self, admin_token: str) -> None:
        """Test that admin token fixture returns a valid JWT token."""
        assert isinstance(admin_token, str)
        assert len(admin_token) > 50  # JWT tokens are lengthy strings
        assert "." in admin_token  # JWT tokens contain dots

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

    def test_regular_user_created(self, regular_user: User) -> None:
        """Test that regular user fixture creates a user with correct properties."""
        assert regular_user.email == "user@example.com"
        assert regular_user.name == "testuser"
        assert regular_user.surname == "testuser"
        assert regular_user.is_active is True
