"""
Demonstration tests for enhanced testing infrastructure (v1.2.0).

This module showcases the new testing capabilities including:
- Fluent Scenario Builder
- Identity-Aware TestClient
- Enhanced factories and fixtures

These tests serve as examples and documentation for the enhanced testing features.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from kwik.testing import IdentityAwareTestClient, Scenario

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from kwik.models import User


class TestScenarioBuilder:
    """Demonstrate the Fluent Scenario Builder capabilities."""

    def test_basic_scenario_creation(self, engine: Engine, admin_user: User) -> None:
        """Test basic scenario creation with fluent API."""
        from kwik.database import create_session

        session = create_session(engine=engine)

        # Create a scenario with multiple users and roles
        scenario = (
            Scenario()
            .with_user(name="john", email="john@test.com", roles=["editor"])
            .with_user(name="jane", admin=True)
            .with_role("editor", permissions=["posts:read", "posts:write"])
            .build(session=session, admin_user=admin_user)
        )

        # Verify users were created
        assert "john" in scenario.users
        assert "jane" in scenario.users

        john = scenario.users["john"]
        jane = scenario.users["jane"]

        assert john.email == "john@test.com"
        assert john.name == "john"
        assert jane.name == "jane"

        # Verify roles and permissions
        assert "editor" in scenario.roles
        assert "admin" in scenario.roles  # Auto-created for admin users

        editor_role = scenario.roles["editor"]
        assert editor_role.name == "editor"
        assert len(editor_role.permissions) >= 2  # At least the assigned permissions


class TestIdentityAwareClient:
    """Demonstrate Identity-Aware TestClient capabilities."""

    def _test_authenticated_requests_as_different_users(
        self,
        auth_client: IdentityAwareTestClient,
        engine: Engine,
        admin_user: User,
    ) -> None:
        """Test making authenticated requests as different users."""
        from kwik.crud import Context, crud_users
        from kwik.database import create_session
        from kwik.schemas import UserRegistration

        # Create test users with the expected password for IdentityAwareTestClient
        session = create_session(engine=engine)
        context = Context(session=session, user=None)

        demo_admin = crud_users.create(
            obj_in=UserRegistration(
                name="demo_admin",
                surname="Demo",
                email="demo_admin@test.com",
                password="testpassword123",
                is_active=True,
            ),
            context=context,
        )

        demo_regular = crud_users.create(
            obj_in=UserRegistration(
                name="demo_regular",
                surname="User",
                email="demo_regular@test.com",
                password="testpassword123",
                is_active=True,
            ),
            context=context,
        )

        # Make request as admin user
        admin_response = auth_client.get_as(demo_admin, "/api/v1/users/me")
        assert admin_response.status_code == HTTPStatus.OK
        admin_data = admin_response.json()
        assert admin_data["email"] == demo_admin.email

        # Make request as regular user
        regular_response = auth_client.get_as(demo_regular, "/api/v1/users/me")
        assert regular_response.status_code == HTTPStatus.OK
        regular_data = regular_response.json()
        assert regular_data["email"] == demo_regular.email

        # Verify different users returned different data
        assert admin_data["email"] != regular_data["email"]
