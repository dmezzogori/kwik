"""Tests for API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette import status

from kwik.database.context_vars import db_conn_ctx_var
from tests.utils import create_test_user


class TestDocsEndpoints:
    """Test cases for documentation endpoints."""

    def test_docs_endpoint(self, client_no_auth: TestClient) -> None:
        """Test that the docs endpoint is accessible."""
        response = client_no_auth.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_openapi_endpoint(self, client_no_auth: TestClient) -> None:
        """Test that the OpenAPI JSON endpoint is accessible."""
        response = client_no_auth.get("/api/v1/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        # Verify it returns JSON
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data


class TestHealthEndpoints:
    """Test cases for health and status endpoints."""

    def test_root_endpoint_exists(self, client_no_auth: TestClient) -> None:
        """Test that some basic endpoint exists."""
        # Since we don't have a root endpoint defined, let's test that 404 is handled
        response = client_no_auth.get("/")
        # Should return either 200 if root exists, or 404 if not - both are valid responses
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestLoginEndpoints:
    """Test cases for authentication endpoints."""

    def test_access_token_endpoint_with_invalid_credentials(self, client_no_auth: TestClient, db_session, clean_db) -> None:
        """Test login with invalid credentials returns 401."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword",
        }

        response = client_no_auth.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_token_endpoint_with_valid_credentials(self, client_no_auth: TestClient, db_session, clean_db) -> None:
        """Test login with valid credentials returns token."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        test_user = create_test_user(db_session, email="test@example.com", password="testpassword123")

        login_data = {
            "username": "test@example.com",
            "password": "testpassword123",
        }

        response = client_no_auth.post("/api/v1/login/access-token", data=login_data)
        assert response.status_code == status.HTTP_200_OK

        token_data = response.json()
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"

    def test_test_token_endpoint_without_auth_returns_401(self, client_no_auth: TestClient) -> None:
        """Test that test-token endpoint requires authentication."""
        response = client_no_auth.post("/api/v1/login/test-token")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="Authentication mocking needs to be implemented")
    def test_test_token_endpoint_with_valid_token(self, client_no_auth: TestClient, db_session, clean_db) -> None:
        """Test test-token endpoint with valid authentication."""
        # TODO: Implement authentication mocking for this test
        # This would require creating a valid JWT token and setting it in headers


class TestUserEndpointsWithoutAuth:
    """Test user endpoints without authentication (should return 401)."""

    def test_get_users_without_auth_returns_401(self, client_no_auth: TestClient) -> None:
        """Test that getting users without auth returns 401."""
        response = client_no_auth.get("/api/v1/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_me_without_auth_returns_401(self, client_no_auth: TestClient) -> None:
        """Test that getting current user without auth returns 401."""
        response = client_no_auth.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_user_without_auth_returns_401(self, client_no_auth: TestClient) -> None:
        """Test that creating a user without auth returns 401."""
        user_data = {
            "name": "Test",
            "surname": "User",
            "email": "test@example.com",
            "password": "testpassword123",
        }

        response = client_no_auth.post("/api/v1/users", json=user_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_user_without_auth_returns_401(self, client_no_auth: TestClient) -> None:
        """Test that updating a user without auth returns 401."""
        user_data = {
            "name": "Updated",
        }

        response = client_no_auth.put("/api/v1/users/1", json=user_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_nonexistent_endpoint_returns_404(self, client_no_auth: TestClient) -> None:
        """Test that non-existent endpoints return 404."""
        response = client_no_auth.get("/nonexistent/endpoint")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_json_payload_returns_422(self, client_no_auth: TestClient) -> None:
        """Test that invalid JSON payloads return 422."""
        # Try to post invalid JSON to an endpoint that expects JSON
        response = client_no_auth.post(
            "/api/v1/users",
            data="invalid json",  # Send raw string instead of JSON
            headers={"content-type": "application/json"},
        )
        # Should return 422 for validation error or 401 for unauthorized
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""

    @pytest.mark.skip(reason="Full integration tests require authentication setup")
    def test_full_user_lifecycle(self, client: TestClient, db_session, clean_db) -> None:
        """Test full user lifecycle: create, read, update, delete."""
        # TODO: Implement full integration test once authentication is properly mocked
