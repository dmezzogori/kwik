"""Tests for IdentityAwareTestClient authentication and request handling."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from kwik.models import User


class TestIdentityAwareClientErrorHandling:
    """Test error handling in IdentityAwareTestClient."""

    def test_authentication_failure_http_error(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test authentication failure when HTTP status is not 200.

        This tests lines 92-93 in client.py where RuntimeError is raised
        for non-200 HTTP status codes during authentication.
        """
        # Create a mock app that returns 401 Unauthorized
        from fastapi import HTTPException  # noqa: PLC0415

        app = FastAPI()

        @app.post("/api/v1/login/access-token")
        def failing_login() -> None:
            raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid credentials")

        failing_client = TestClient(app)
        identity_client = IdentityAwareTestClient(failing_client)

        # Attempt to make authenticated request, should fail with RuntimeError
        with pytest.raises(RuntimeError, match=r"Authentication failed for user .+: 401"):
            identity_client.get_as(test_user_for_testing, "/test-endpoint")

    def test_authentication_invalid_json_response(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test authentication failure when JSON response is malformed.

        This tests lines 98-100 in client.py where RuntimeError is raised
        when the authentication response doesn't contain expected fields.
        """
        # Create a mock app that returns invalid JSON structure
        app = FastAPI()

        @app.post("/api/v1/login/access-token")
        def malformed_login() -> dict[str, str]:
            return {"invalid": "response"}  # Missing 'access_token' field

        malformed_client = TestClient(app)
        identity_client = IdentityAwareTestClient(malformed_client)

        # Attempt to make authenticated request, should fail with RuntimeError
        with pytest.raises(RuntimeError, match=r"Invalid authentication response for user .+: 'access_token'"):
            identity_client.get_as(test_user_for_testing, "/test-endpoint")

    def test_authentication_json_decode_error(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test authentication failure when response cannot be decoded as JSON.

        This also tests lines 98-100 in client.py for ValueError handling
        when JSON decoding fails.
        """
        # Mock the client to return invalid JSON
        mock_client = Mock(spec=TestClient)
        mock_response = Mock()
        mock_response.status_code = HTTPStatus.OK
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.post.return_value = mock_response

        identity_client = IdentityAwareTestClient(mock_client)

        # Attempt to make authenticated request, should fail with RuntimeError
        with pytest.raises(RuntimeError, match=r"Invalid authentication response for user .+: Invalid JSON"):
            identity_client.get_as(test_user_for_testing, "/test-endpoint")


class TestIdentityAwareClientAuth:
    """Test authentication behavior in IdentityAwareTestClient."""

    def test_unrecognized_user_fallback_password(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test fallback password behavior for unrecognized user emails.

        This tests line 82 in client.py where users with unrecognized email
        patterns get the default "testpassword123" password.
        """
        received_data = {}

        # Instead of using a real FastAPI app, let's mock the client directly
        mock_test_client = Mock(spec=TestClient)
        mock_auth_response = Mock()
        mock_auth_response.status_code = HTTPStatus.OK
        mock_auth_response.json.return_value = {"access_token": "test_token_123", "token_type": "bearer"}

        mock_endpoint_response = Mock()
        mock_endpoint_response.status_code = HTTPStatus.OK
        mock_endpoint_response.json.return_value = {"message": "success"}

        def mock_post_handler(url: str, **kwargs: dict) -> Mock:
            if "login" in url:
                # Capture the form data
                if "data" in kwargs:
                    received_data.update(kwargs["data"])
                return mock_auth_response
            return Mock()

        def mock_get_handler(url: str, **kwargs: dict) -> Mock:  # noqa: ARG001
            return mock_endpoint_response

        mock_test_client.post = mock_post_handler
        mock_test_client.get = mock_get_handler

        identity_client = IdentityAwareTestClient(mock_test_client)

        # Add id to user for caching
        test_user_for_testing.id = 998  # Mock ID for caching

        # The test_user_for_testing has email "unknown.pattern@testing.com"
        # which doesn't match any known patterns, so should use fallback
        response = identity_client.get_as(test_user_for_testing, "/test-endpoint")

        assert response.status_code == HTTPStatus.OK
        assert received_data["password"] == "testpassword123"  # Fallback password used
        assert received_data["username"] == test_user_for_testing.email

    def test_regular_user_password_pattern(
        self,
        session,  # noqa: ARG002, ANN001
        admin_context,  # noqa: ARG002, ANN001
    ) -> None:
        """Test that regular@example.com uses the regular password pattern."""
        # Create mock user with regular@example.com pattern (no DB creation needed)
        regular_user = Mock()
        regular_user.email = "regular@example.com"
        regular_user.name = "regular"
        regular_user.id = 999  # Mock ID for caching

        received_data = {}

        # Mock the TestClient directly
        mock_test_client = Mock(spec=TestClient)
        mock_auth_response = Mock()
        mock_auth_response.status_code = HTTPStatus.OK
        mock_auth_response.json.return_value = {"access_token": "test_token_123", "token_type": "bearer"}

        mock_endpoint_response = Mock()
        mock_endpoint_response.status_code = HTTPStatus.OK
        mock_endpoint_response.json.return_value = {"message": "success"}

        def mock_post_handler(url: str, **kwargs: dict) -> Mock:
            if "login" in url:
                # Capture the form data
                if "data" in kwargs:
                    received_data.update(kwargs["data"])
                return mock_auth_response
            return Mock()

        def mock_get_handler(url: str, **kwargs: dict) -> Mock:  # noqa: ARG001
            return mock_endpoint_response

        mock_test_client.post = mock_post_handler
        mock_test_client.get = mock_get_handler

        identity_client = IdentityAwareTestClient(mock_test_client)

        response = identity_client.get_as(regular_user, "/test-endpoint")

        assert response.status_code == HTTPStatus.OK
        assert received_data["password"] == "regularpassword123"  # Specific regular password
        assert received_data["username"] == "regular@example.com"

    def test_successful_authentication_and_request(
        self,
        identity_client_no_settings: IdentityAwareTestClient,  # noqa: ARG002
        test_user_for_testing: User,
    ) -> None:
        """Test successful authentication and subsequent request."""
        # Mock the test endpoint
        mock_app = FastAPI()

        @mock_app.post("/api/v1/login/access-token")
        def login() -> dict[str, str]:
            return {"access_token": "test_token_123", "token_type": "bearer"}

        @mock_app.get("/test-endpoint")
        def test_endpoint() -> dict[str, str]:
            return {"message": "success"}

        client = TestClient(mock_app)
        identity_client = IdentityAwareTestClient(client)

        # Make authenticated request
        response = identity_client.get_as(test_user_for_testing, "/test-endpoint")

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"message": "success"}

    def test_token_caching_behavior(
        self,
        identity_client_no_settings: IdentityAwareTestClient,  # noqa: ARG002
        test_user_for_testing: User,
    ) -> None:
        """Test that authentication tokens are cached and reused."""
        call_count = 0

        # Mock the test endpoints with call counting
        mock_app = FastAPI()

        @mock_app.post("/api/v1/login/access-token")
        def login() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"access_token": f"test_token_{call_count}", "token_type": "bearer"}

        @mock_app.get("/test-endpoint")
        def test_endpoint() -> dict[str, str]:
            return {"message": "success"}

        client = TestClient(mock_app)
        identity_client = IdentityAwareTestClient(client)

        # Make first authenticated request
        response1 = identity_client.get_as(test_user_for_testing, "/test-endpoint")
        assert response1.status_code == HTTPStatus.OK
        assert call_count == 1  # Authentication called once

        # Make second authenticated request with same user
        response2 = identity_client.get_as(test_user_for_testing, "/test-endpoint")
        assert response2.status_code == HTTPStatus.OK
        assert call_count == 1  # Authentication not called again (cached)


class TestIdentityAwareClientMethods:
    """Test HTTP method coverage in IdentityAwareTestClient."""

    def test_patch_as_method(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test the patch_as method functionality.

        This tests line 197 in client.py to ensure the patch_as method
        is properly tested and covered.
        """
        # Mock app with PATCH endpoint
        mock_app = FastAPI()

        @mock_app.post("/api/v1/login/access-token")
        def login() -> dict[str, str]:
            return {"access_token": "test_token_123", "token_type": "bearer"}

        @mock_app.patch("/test-endpoint")
        def patch_endpoint() -> dict[str, str]:
            return {"message": "patched", "method": "PATCH"}

        client = TestClient(mock_app)
        identity_client = IdentityAwareTestClient(client)

        # Make authenticated PATCH request
        response = identity_client.patch_as(test_user_for_testing, "/test-endpoint", json={"field": "value"})

        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"message": "patched", "method": "PATCH"}

    def test_clear_token_cache_method(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test the clear_token_cache method functionality.

        This tests line 216 in client.py to ensure the clear_token_cache method
        clears the internal token cache and forces re-authentication.
        """
        auth_call_count = 0

        # Mock app that counts authentication calls
        mock_app = FastAPI()

        @mock_app.post("/api/v1/login/access-token")
        def login() -> dict[str, str]:
            nonlocal auth_call_count
            auth_call_count += 1
            return {"access_token": f"token_{auth_call_count}", "token_type": "bearer"}

        @mock_app.get("/test-endpoint")
        def test_endpoint() -> dict[str, str]:
            return {"message": "success"}

        client = TestClient(mock_app)
        identity_client = IdentityAwareTestClient(client)

        # First request - should authenticate
        response1 = identity_client.get_as(test_user_for_testing, "/test-endpoint")
        assert response1.status_code == HTTPStatus.OK
        assert auth_call_count == 1

        # Second request - should use cached token
        response2 = identity_client.get_as(test_user_for_testing, "/test-endpoint")
        assert response2.status_code == HTTPStatus.OK
        assert auth_call_count == 1  # Still 1, used cache

        # Clear the token cache
        identity_client.clear_token_cache()

        # Third request - should authenticate again after cache clear
        response3 = identity_client.get_as(test_user_for_testing, "/test-endpoint")
        assert response3.status_code == HTTPStatus.OK
        expected_auth_count = 2  # Increased to 2, re-authenticated
        assert auth_call_count == expected_auth_count
