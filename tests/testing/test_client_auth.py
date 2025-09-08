"""Tests for IdentityAwareTestClient authentication password logic."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from fastapi.testclient import TestClient

from kwik.testing import IdentityAwareTestClient

if TYPE_CHECKING:
    from kwik.models import User


class TestIdentityAwareClientPasswordLogic:
    """Test password selection logic in IdentityAwareTestClient."""

    def test_unrecognized_user_fallback_password(
        self,
        test_user_for_testing: User,
    ) -> None:
        """
        Test fallback password behavior for unrecognized user emails.

        This tests line 82 in client.py where users with unrecognized email
        patterns get the default "testpassword123" password.
        """
        # Mock the HTTP client to capture what password is sent
        mock_client = Mock(spec=TestClient)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token", "token_type": "bearer"}

        captured_data = {}

        def capture_post(*args, **kwargs) -> Mock:  # noqa: ANN002, ANN003, ARG001
            captured_data.update(kwargs.get("data", {}))
            return mock_response

        mock_client.post = capture_post
        mock_client.get = Mock(return_value=Mock(status_code=200))

        identity_client = IdentityAwareTestClient(mock_client)

        # Make request which should trigger authentication
        identity_client.get_as(test_user_for_testing, "/test-endpoint")

        # Verify fallback password was used for unrecognized email
        assert captured_data["password"] == "testpassword123"
        assert captured_data["username"] == test_user_for_testing.email

    def test_regular_user_specific_password(
        self,
        session,  # noqa: ARG002, ANN001
        admin_context,  # noqa: ARG002, ANN001
    ) -> None:
        """Test that regular@example.com uses the specific regular password."""
        # Create mock user with regular@example.com pattern (no DB creation needed)
        regular_user = Mock()
        regular_user.email = "regular@example.com"
        regular_user.name = "regular"

        # Mock the HTTP client to capture what password is sent
        mock_client = Mock(spec=TestClient)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token", "token_type": "bearer"}

        captured_data = {}

        def capture_post(*args, **kwargs) -> Mock:  # noqa: ANN002, ANN003, ARG001
            captured_data.update(kwargs.get("data", {}))
            return mock_response

        mock_client.post = capture_post
        mock_client.get = Mock(return_value=Mock(status_code=200))

        identity_client = IdentityAwareTestClient(mock_client)

        # Make request which should trigger authentication
        identity_client.get_as(regular_user, "/test-endpoint")

        # Verify regular-specific password was used
        assert captured_data["password"] == "regularpassword123"
        assert captured_data["username"] == "regular@example.com"

    def test_superuser_password_with_settings(
        self,
        session,  # noqa: ARG002, ANN001
        admin_context,  # noqa: ARG002, ANN001
        settings,  # noqa: ANN001
    ) -> None:
        """Test that FIRST_SUPERUSER email uses settings password."""
        # Create mock user with FIRST_SUPERUSER email (no DB creation needed)
        superuser = Mock()
        superuser.email = settings.FIRST_SUPERUSER
        superuser.name = "superuser"

        # Mock the HTTP client to capture what password is sent
        mock_client = Mock(spec=TestClient)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token", "token_type": "bearer"}

        captured_data = {}

        def capture_post(*args, **kwargs) -> Mock:  # noqa: ANN002, ANN003, ARG001
            captured_data.update(kwargs.get("data", {}))
            return mock_response

        mock_client.post = capture_post
        mock_client.get = Mock(return_value=Mock(status_code=200))

        identity_client = IdentityAwareTestClient(mock_client, settings)

        # Make request which should trigger authentication
        identity_client.get_as(superuser, "/test-endpoint")

        # Verify FIRST_SUPERUSER_PASSWORD was used
        assert captured_data["password"] == settings.FIRST_SUPERUSER_PASSWORD
        assert captured_data["username"] == settings.FIRST_SUPERUSER
