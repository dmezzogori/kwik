"""Tests for the Scenario builder in kwik.testing.scenario."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from kwik.testing.scenario import Scenario, ScenarioResult

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.crud import UserCtx


class TestScenarioParameterHandling:
    """Test parameter handling in Scenario builder methods."""

    def test_with_user_email_auto_generation(self) -> None:
        """
        Test email auto-generation when email is None.

        This tests line 115 in scenario.py where email is auto-generated
        from the user's name when email=None.
        """
        scenario = Scenario()

        # Call with_user without providing email
        result_scenario = scenario.with_user(name="testuser")

        # Check that the email was auto-generated
        user_spec = result_scenario._user_specs[0]
        assert user_spec.email == "testuser@test.com"
        assert user_spec.name == "testuser"

    def test_with_user_admin_role_appending(self) -> None:
        """
        Test admin role appending when admin=True.

        This tests line 119 in scenario.py where "admin" role is appended
        to the roles list when admin=True.
        """
        scenario = Scenario()

        # Call with_user with admin=True and some existing roles
        result_scenario = scenario.with_user(name="adminuser", admin=True, roles=["editor", "viewer"])

        # Check that "admin" was appended to the roles
        user_spec = result_scenario._user_specs[0]
        assert user_spec.admin is True
        assert "admin" in user_spec.roles
        assert "editor" in user_spec.roles
        assert "viewer" in user_spec.roles
        expected_role_count = 3  # editor, viewer, admin
        assert len(user_spec.roles) == expected_role_count

    def test_with_user_admin_role_appending_empty_roles(self) -> None:
        """Test admin role appending when no existing roles."""
        scenario = Scenario()

        # Call with_user with admin=True and no roles
        result_scenario = scenario.with_user(name="adminuser", admin=True)

        # Check that "admin" was added to initially empty roles
        user_spec = result_scenario._user_specs[0]
        assert user_spec.admin is True
        assert user_spec.roles == ["admin"]

    def test_with_admin_user_convenience_method(self) -> None:
        """
        Test the with_admin_user convenience method.

        This tests line 159 in scenario.py where the with_admin_user method
        creates an admin user with default parameters.
        """
        scenario = Scenario()

        # Call with_admin_user with defaults
        result_scenario = scenario.with_admin_user()

        # Check that admin user was created with correct defaults
        user_spec = result_scenario._user_specs[0]
        assert user_spec.name == "admin"
        assert user_spec.surname == "Admin"
        assert user_spec.email == "admin@test.com"
        assert user_spec.password == "adminpassword123"
        assert user_spec.admin is True
        assert "admin" in user_spec.roles

    def test_with_admin_user_custom_parameters(self) -> None:
        """Test with_admin_user with custom parameters."""
        scenario = Scenario()

        # Call with_admin_user with custom parameters
        result_scenario = scenario.with_admin_user(
            name="superadmin", surname="Super", email="super@admin.com", password="superpass123"
        )

        # Check that custom parameters were used
        user_spec = result_scenario._user_specs[0]
        assert user_spec.name == "superadmin"
        assert user_spec.surname == "Super"
        assert user_spec.email == "super@admin.com"
        assert user_spec.password == "superpass123"
        assert user_spec.admin is True
        assert "admin" in user_spec.roles

    def test_with_role_custom_permission_tracking(self) -> None:
        """
        Test custom permission tracking in with_role.

        This tests line 193 in scenario.py where custom permissions
        are added to the _custom_permissions set.
        """
        scenario = Scenario()

        # Call with_role with custom permissions
        result_scenario = scenario.with_role(name="editor", permissions=["posts:read", "posts:write", "custom:action"])

        # Check that custom permissions were tracked
        assert "posts:read" in result_scenario._custom_permissions
        assert "posts:write" in result_scenario._custom_permissions
        assert "custom:action" in result_scenario._custom_permissions
        expected_custom_permission_count = 3
        assert len(result_scenario._custom_permissions) == expected_custom_permission_count

    def test_with_role_no_permissions(self) -> None:
        """Test with_role without permissions doesn't affect custom permissions."""
        scenario = Scenario()

        # Call with_role without permissions
        result_scenario = scenario.with_role(name="basic_role")

        # Check that no custom permissions were added
        assert len(result_scenario._custom_permissions) == 0

    def test_with_role_empty_permissions_list(self) -> None:
        """Test with_role with empty permissions list."""
        scenario = Scenario()

        # Call with_role with empty permissions list
        result_scenario = scenario.with_role(name="empty_role", permissions=[])

        # Check that no custom permissions were added
        assert len(result_scenario._custom_permissions) == 0


class TestScenarioBuilding:
    """Test scenario building functionality."""

    def test_scenario_chaining(self) -> None:
        """Test that scenario methods can be chained together."""
        scenario = (
            Scenario()
            .with_user(name="john", email="john@test.com")
            .with_user(name="jane", admin=True)
            .with_role("editor", permissions=["posts:read", "posts:write"])
            .with_admin_user(name="superadmin")
        )

        # Verify all specs were added
        expected_user_count = 3
        assert len(scenario._user_specs) == expected_user_count
        assert len(scenario._role_specs) == 1
        expected_custom_permission_count = 2
        assert len(scenario._custom_permissions) == expected_custom_permission_count

    def test_scenario_result_structure(self) -> None:
        """Test ScenarioResult dataclass structure."""
        result = ScenarioResult()

        # Verify empty defaults
        assert isinstance(result.users, dict)
        assert isinstance(result.roles, dict)
        assert isinstance(result.permissions, dict)
        assert len(result.users) == 0
        assert len(result.roles) == 0
        assert len(result.permissions) == 0


class TestScenarioValidationErrors:
    """Test validation error handling in Scenario builder."""

    def test_build_missing_admin_user_for_permissions(
        self,
        session: Session,
    ) -> None:
        """
        Test ValueError when admin_user is required but not provided for permissions.

        This tests lines 232-233 in scenario.py where ValueError is raised
        when admin_user is None but permissions are defined.
        """
        scenario = Scenario().with_role("editor", permissions=["custom:permission"])

        # Try to build without admin_user (should fail)
        with pytest.raises(ValueError, match="admin_user is required for scenarios with permissions"):
            scenario.build(session=session, admin_user=None)

    def test_build_missing_admin_user_for_roles(
        self,
        session: Session,
    ) -> None:
        """
        Test ValueError when admin_user is required but not provided for roles.

        This tests lines 232-233 in scenario.py where ValueError is raised
        when admin_user is None but roles are defined.
        """
        scenario = Scenario().with_role("basic_role")

        # Try to build without admin_user (should fail)
        with pytest.raises(ValueError, match="admin_user is required for scenarios with permissions"):
            scenario.build(session=session, admin_user=None)

    def test_build_missing_admin_user_for_admin_users(
        self,
        session: Session,
    ) -> None:
        """
        Test ValueError when admin_user is required but not provided for admin users.

        This tests lines 232-233 in scenario.py where ValueError is raised
        when admin_user is None but admin users are specified.
        """
        scenario = Scenario().with_user(name="testadmin", admin=True)

        # Try to build without admin_user (should fail)
        with pytest.raises(ValueError, match="admin_user is required for scenarios with permissions"):
            scenario.build(session=session, admin_user=None)

    def test_build_missing_admin_user_for_user_roles(
        self,
        session: Session,
    ) -> None:
        """
        Test ValueError when admin_user is required but not provided for user role assignments.

        This tests lines 232-233 in scenario.py where ValueError is raised
        when admin_user is None but users have role assignments.
        """
        scenario = Scenario().with_user(name="testuser", roles=["editor"])

        # Try to build without admin_user (should fail)
        with pytest.raises(ValueError, match="admin_user is required for scenarios with permissions"):
            scenario.build(session=session, admin_user=None)

    def test_build_missing_role_for_user_assignment(
        self,
        session: Session,
        admin_context: UserCtx,
    ) -> None:
        """
        Test ValueError when assigning non-existent role to user.

        This tests lines 326-327 in scenario.py where ValueError is raised
        when trying to assign a role that doesn't exist to a user.
        """
        scenario = Scenario().with_user(name="testuser", roles=["nonexistent_role"])

        # Try to build with non-existent role (should fail)
        with pytest.raises(ValueError, match="Role 'nonexistent_role' not found for user 'testuser'"):
            scenario.build(session=session, admin_user=admin_context.user)


class TestScenarioAutoCreationLogic:
    """Test auto-creation logic in Scenario builder."""

    def test_admin_role_auto_creation_for_admin_users(
        self,
        session: Session,
        admin_context: UserCtx,
    ) -> None:
        """
        Test automatic admin role creation when admin users exist but no admin role.

        This tests lines 286-289 in scenario.py where an admin role is automatically
        created when admin users are specified but no "admin" role exists.
        """
        # Mock the necessary CRUD operations
        with (
            patch("kwik.testing.scenario.crud_roles") as mock_crud_roles,
            patch("kwik.testing.scenario.crud_permissions") as mock_crud_perms,
            patch("kwik.testing.scenario.crud_users") as mock_crud_users,
            patch("kwik.testing.scenario.Permissions") as mock_permissions_enum,
        ):
            # Setup mocks
            mock_admin_role = Mock()
            mock_admin_role.name = "admin"
            mock_crud_roles.create.return_value = mock_admin_role

            mock_permission = Mock()
            mock_permission.name = "test:permission"
            mock_crud_perms.get_by_name.return_value = mock_permission

            mock_user = Mock()
            mock_user.name = "adminuser"
            mock_crud_users.create.return_value = mock_user

            # Mock the Permissions enum
            mock_permissions_enum.__iter__.return_value = [Mock(value="test:permission")]

            # Create scenario with admin user but no explicit admin role
            scenario = Scenario().with_user(name="adminuser", admin=True)

            # Build the scenario
            _result = scenario.build(session=session, admin_user=admin_context.user)

            # Verify that admin role was auto-created
            mock_crud_roles.create.assert_called()

            # We can't easily verify the exact RoleDefinition without complex mocking,
            # but we can verify that create was called, which means the auto-creation logic ran
            assert mock_crud_roles.create.called

    def test_no_admin_role_auto_creation_when_admin_role_exists(
        self,
        session: Session,
        admin_context: UserCtx,
    ) -> None:
        """
        Test that admin role is NOT auto-created when it already exists.

        This verifies that lines 286-289 are only executed when no admin role exists.
        """
        # Mock the necessary CRUD operations
        with (
            patch("kwik.testing.scenario.crud_roles") as mock_crud_roles,
            patch("kwik.testing.scenario.crud_permissions"),
            patch("kwik.testing.scenario.crud_users") as mock_crud_users,
        ):
            # Setup mocks
            mock_admin_role = Mock()
            mock_admin_role.name = "admin"
            mock_crud_roles.create.return_value = mock_admin_role

            mock_user = Mock()
            mock_user.name = "adminuser"
            mock_crud_users.create.return_value = mock_user

            # Create scenario with explicit admin role AND admin user
            scenario = Scenario().with_role("admin", is_active=True).with_user(name="adminuser", admin=True)

            # Build the scenario
            _result = scenario.build(session=session, admin_user=admin_context.user)

            # Verify that admin role was only created once (the explicit one)
            assert mock_crud_roles.create.call_count == 1

    def test_no_admin_role_auto_creation_without_admin_users(
        self,
        session: Session,
        admin_context: UserCtx,
    ) -> None:
        """
        Test that admin role is NOT auto-created when no admin users exist.

        This verifies that lines 286-289 are only executed when admin users exist.
        """
        # Mock the necessary CRUD operations
        with (
            patch("kwik.testing.scenario.crud_roles") as mock_crud_roles,
            patch("kwik.testing.scenario.crud_users") as mock_crud_users,
        ):
            # Setup mocks
            mock_user = Mock()
            mock_user.name = "regularuser"
            mock_crud_users.create.return_value = mock_user

            # Create scenario with regular user (no admin users)
            scenario = Scenario().with_user(name="regularuser", admin=False)

            # Build the scenario
            _result = scenario.build(session=session, admin_user=admin_context.user)

            # Verify that NO admin role was auto-created
            mock_crud_roles.create.assert_not_called()
