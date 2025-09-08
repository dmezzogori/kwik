"""Tests for factory fixtures in kwik.testing.fixtures.factories."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.crud import UserCtx
    from kwik.models import Permission, Role, User


class TestUserFactory:
    """Test the user_factory fixture functionality."""

    def test_user_factory_basic_creation(
        self,
        user_factory: Callable[..., User],
    ) -> None:
        """Test basic user creation with default parameters."""
        _user = user_factory()

        assert _user.name == "testuser"
        assert _user.surname == "testsurname"
        assert _user.email == "testuser@test.com"
        assert _user.is_active is True

    def test_user_factory_custom_parameters(
        self,
        user_factory: Callable[..., User],
    ) -> None:
        """Test user creation with custom parameters."""
        _user = user_factory(
            name="john",
            surname="doe",
            email="john.doe@custom.com",
            password="custompass123",
            is_active=False,
        )

        assert _user.name == "john"
        assert _user.surname == "doe"
        assert _user.email == "john.doe@custom.com"
        assert _user.is_active is False

    def test_user_factory_email_auto_generation(
        self,
        user_factory: Callable[..., User],
    ) -> None:
        """Test automatic email generation when email is None."""
        _user = user_factory(name="alice", email=None)

        assert _user.name == "alice"
        assert _user.email == "alice@test.com"

    def test_user_factory_admin_context_path(
        self,
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """
        Test that admin context is used when creating admin users or users with roles.

        This tests line 81 in factories.py where the admin context path is taken
        for users with admin=True or roles specified.
        """
        # Mock the Scenario class to verify admin_user is passed correctly
        with patch("kwik.testing.fixtures.factories.Scenario") as mock_scenario_class:
            mock_scenario_instance = Mock()
            mock_result = Mock()
            mock_result.users = {"testadmin": Mock()}

            mock_scenario_instance.with_user.return_value = mock_scenario_instance
            mock_scenario_instance.build.return_value = mock_result
            mock_scenario_class.return_value = mock_scenario_instance

            # Test admin user creation
            _user = user_factory(name="testadmin", admin=True)

            # Verify that build was called with admin_context
            mock_scenario_instance.build.assert_called_once_with(
                session=admin_context.session, admin_user=admin_context.user
            )

            # Verify the with_user call included admin=True
            mock_scenario_instance.with_user.assert_called_once_with(
                name="testadmin",
                surname="testsurname",
                email="testadmin@test.com",
                password="testpassword123",
                is_active=True,
                admin=True,
                roles=[],
            )

    def test_user_factory_roles_context_path(
        self,
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """
        Test that admin context is used when creating users with roles.

        This also tests line 81 in factories.py where the admin context path is taken
        for users with roles specified.
        """
        # Mock the Scenario class to verify admin_user is passed correctly
        with patch("kwik.testing.fixtures.factories.Scenario") as mock_scenario_class:
            mock_scenario_instance = Mock()
            mock_result = Mock()
            mock_result.users = {"roleduser": Mock()}

            mock_scenario_instance.with_user.return_value = mock_scenario_instance
            mock_scenario_instance.build.return_value = mock_result
            mock_scenario_class.return_value = mock_scenario_instance

            # Test user with roles creation
            _user = user_factory(name="roleduser", roles=["editor", "viewer"])

            # Verify that build was called with admin_context
            mock_scenario_instance.build.assert_called_once_with(
                session=admin_context.session, admin_user=admin_context.user
            )

            # Verify the with_user call included roles
            mock_scenario_instance.with_user.assert_called_once_with(
                name="roleduser",
                surname="testsurname",
                email="roleduser@test.com",
                password="testpassword123",
                is_active=True,
                admin=False,
                roles=["editor", "viewer"],
            )

    def test_user_factory_no_admin_context_path(
        self,
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """
        Test that no-user context is used for regular users without admin or roles.

        This verifies the else path in line 81-85 of factories.py.
        """
        # Mock the Context and Scenario classes
        with (
            patch("kwik.testing.fixtures.factories.Context") as mock_context_class,
            patch("kwik.testing.fixtures.factories.Scenario") as mock_scenario_class,
        ):
            mock_no_user_context = Mock()
            mock_context_class.return_value = mock_no_user_context

            mock_scenario_instance = Mock()
            mock_result = Mock()
            mock_result.users = {"regularuser": Mock()}

            mock_scenario_instance.with_user.return_value = mock_scenario_instance
            mock_scenario_instance.build.return_value = mock_result
            mock_scenario_class.return_value = mock_scenario_instance

            # Test regular user creation (no admin, no roles)
            _user = user_factory(name="regularuser", admin=False, roles=None)

            # Verify Context was called with session and user=None
            mock_context_class.assert_called_once_with(session=admin_context.session, user=None)

            # Verify that build was called with no_user_context.session but admin_context.user
            mock_scenario_instance.build.assert_called_once_with(
                session=mock_no_user_context.session, admin_user=admin_context.user
            )


class TestRoleFactory:
    """Test the role_factory fixture functionality."""

    def test_role_factory_basic_creation(
        self,
        role_factory: Callable[..., Role],
    ) -> None:
        """Test basic role creation with default parameters."""
        _role = role_factory()

        assert _role.name == "test_role"
        assert _role.is_active is True

    def test_role_factory_custom_parameters(
        self,
        role_factory: Callable[..., Role],
    ) -> None:
        """Test role creation with custom parameters."""
        _role = role_factory(
            name="editor",
            is_active=False,
            permissions=["posts:read", "posts:write"],
        )

        assert _role.name == "editor"
        assert _role.is_active is False


class TestPermissionFactory:
    """Test the permission_factory fixture functionality."""

    def test_permission_factory_basic_creation(
        self,
        permission_factory: Callable[..., Permission],
    ) -> None:
        """Test basic permission creation with default parameters."""
        _permission = permission_factory()

        assert _permission.name == "test_permission"

    def test_permission_factory_custom_name(
        self,
        permission_factory: Callable[..., Permission],
    ) -> None:
        """Test permission creation with custom name."""
        _permission = permission_factory(name="custom:action")

        assert _permission.name == "custom:action"
