"""Tests for user CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from kwik.crud import NoUserCtx, crud_users
from kwik.exceptions import AuthenticationFailedError, EntityNotFoundError, InactiveUserError, UserNotFoundError
from kwik.schemas import UserPasswordChange, UserProfileUpdate, UserRegistration

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.models import User


class TestUserCRUD:
    """Test cases for user CRUD operations."""

    def test_create_user(self, user_factory: Callable[..., User]) -> None:
        """Test creating a new user."""
        created_user = user_factory(
            name="Test",
            surname="User",
            email="test@example.com",
            password="testpassword123",
            is_active=True,
        )

        assert created_user.id is not None
        assert created_user.name == "Test"
        assert created_user.surname == "User"
        assert created_user.email == "test@example.com"
        assert created_user.is_active is True
        assert created_user.hashed_password != "testpassword123"  # Should be hashed

    def test_create_user_duplicate_email_raises_error(self, no_user_context: NoUserCtx) -> None:
        """Test that creating a user with duplicate email raises an error."""
        # Create first user
        user_data = UserRegistration(
            name="Test1",
            surname="User1",
            email="test@example.com",
            password="testpassword123",
        )
        crud_users.create(obj_in=user_data, context=no_user_context)

        # Try to create second user with same email
        with pytest.raises(IntegrityError):
            crud_users.create(obj_in=user_data, context=no_user_context)

    def test_get_user_by_id(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test getting a user by ID."""
        # Create a test user
        user = user_factory()

        # Get the user by ID
        retrieved_user = crud_users.get(entity_id=user.id, context=no_user_context)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email

    def test_get_user_by_nonexistent_id_returns_none(self, no_user_context: NoUserCtx) -> None:
        """Test getting a user by non-existent ID returns None."""
        retrieved_user = crud_users.get(entity_id=99999, context=no_user_context)
        assert retrieved_user is None

        with pytest.raises(EntityNotFoundError):
            crud_users.get_if_exist(entity_id=99999, context=no_user_context)

    def test_get_user_by_email(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test getting a user by email."""
        # Create a test user
        user = user_factory()

        # Get the user by email
        retrieved_user = crud_users.get_by_email(email=user.email, context=no_user_context)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email

    def test_get_user_by_nonexistent_email_returns_none(self, no_user_context: NoUserCtx) -> None:
        """Test getting a user by non-existent email returns None."""
        retrieved_user = crud_users.get_by_email(email="nonexistent@example.com", context=no_user_context)
        assert retrieved_user is None

    def test_update_user(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test updating a user."""
        # Create a test user
        user = user_factory()

        # Update the user
        update_data = UserProfileUpdate(
            name="updated_name",
            surname="updated_surname",
            email="updated@example.com",
            is_active=False,
        )
        updated_user = crud_users.update(entity_id=user.id, obj_in=update_data, context=no_user_context)

        assert updated_user.id == user.id
        assert updated_user.name == "updated_name"
        assert updated_user.surname == "updated_surname"
        assert updated_user.email == "updated@example.com"
        assert updated_user.is_active is False

    def test_get_if_exist_with_existing_user(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test get_if_exist with an existing user."""
        # Create a test user
        user = user_factory()

        # Get the user using get_if_exist
        retrieved_user = crud_users.get_if_exist(entity_id=user.id, context=no_user_context)

        assert retrieved_user.id == user.id

    def test_get_if_exist_with_nonexistent_user_raises_error(self, no_user_context: NoUserCtx) -> None:
        """Test get_if_exist with non-existent user raises NotFound."""
        with pytest.raises(EntityNotFoundError):
            crud_users.get_if_exist(entity_id=99999, context=no_user_context)

    def test_get_multi_users(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test getting multiple users with pagination."""
        # Get current user count first
        initial_count, _ = crud_users.get_multi(skip=0, limit=100, context=no_user_context)

        # Test constants
        test_users = 5
        page_limit = 3
        expected_total = initial_count + test_users

        # Create multiple test users
        users = []
        for i in range(test_users):
            user = user_factory(email=f"user{i}@example.com", name=f"User{i}")
            users.append(user)

        # Get multiple users
        count, retrieved_users = crud_users.get_multi(skip=0, limit=page_limit, context=no_user_context)

        assert count == expected_total  # Total count
        assert len(retrieved_users) == page_limit  # Limited to 3

        # Test pagination - second page should have remaining users up to page_limit
        count, second_page = crud_users.get_multi(skip=page_limit, limit=page_limit, context=no_user_context)
        assert count == expected_total
        expected_remaining = min(page_limit, expected_total - page_limit)
        assert len(second_page) == expected_remaining  # Remaining users up to limit

    def test_get_multi_with_filters(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test getting multiple users with filters."""
        # Get initial active user count (includes session-scoped admin user who is active)
        initial_active_count, _ = crud_users.get_multi(is_active=True, context=no_user_context)

        # Create test users with different attributes
        user_factory(email="active@example.com", is_active=True)
        user_factory(email="inactive@example.com", is_active=False)

        # Filter by is_active
        count, active_users = crud_users.get_multi(is_active=True, context=no_user_context)
        assert count == initial_active_count + 1  # Original active + new active user
        assert all(user.is_active is True for user in active_users)

        count, inactive_users = crud_users.get_multi(is_active=False, context=no_user_context)
        assert count == 1  # Only the inactive user we just created
        assert inactive_users[0].is_active is False

    def test_delete_user(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test deleting a user."""
        # Create a test user
        user = user_factory()
        user_id = user.id

        # Delete the user
        deleted_user = crud_users.delete(entity_id=user_id, context=no_user_context)

        assert deleted_user is not None
        assert deleted_user.id == user_id

        # Verify user is deleted
        retrieved_user = crud_users.get(entity_id=user_id, context=no_user_context)
        assert retrieved_user is None

    def test_authenticate_with_valid_credentials(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test authenticating with valid email and password."""
        # Create a test user with known password
        password = "testpassword123"
        user = user_factory(email="auth@example.com", password=password)

        # Authenticate with correct credentials
        authenticated_user = crud_users.authenticate(
            email="auth@example.com", password=password, context=no_user_context
        )

        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.email == "auth@example.com"

    def test_authenticate_with_invalid_email_raises_error(self, no_user_context: NoUserCtx) -> None:
        """Test authenticating with invalid email raises AuthenticationFailedError."""
        with pytest.raises(AuthenticationFailedError):
            crud_users.authenticate(email="nonexistent@example.com", password="anypassword", context=no_user_context)

    def test_authenticate_with_invalid_password_raises_error(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test authenticating with invalid password raises AuthenticationFailedError."""
        # Create a test user
        user_factory(email="auth@example.com", password="correctpassword")

        # Try to authenticate with wrong password
        with pytest.raises(AuthenticationFailedError):
            crud_users.authenticate(email="auth@example.com", password="wrongpassword", context=no_user_context)

    def test_change_password_with_valid_old_password(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test changing password with valid old password."""
        # Create a test user with known password
        old_password = "oldpassword123"
        user = user_factory(password=old_password)
        original_hash = user.hashed_password

        # Change password
        password_change = UserPasswordChange(old_password=old_password, new_password="newpassword456")
        updated_user = crud_users.change_password(user_id=user.id, obj_in=password_change, context=no_user_context)

        assert updated_user.id == user.id
        assert updated_user.hashed_password != original_hash  # Password should be changed

        # Verify old password no longer works
        with pytest.raises(AuthenticationFailedError):
            crud_users.authenticate(email=user.email, password=old_password, context=no_user_context)

        # Verify new password works
        authenticated_user = crud_users.authenticate(
            email=user.email, password="newpassword456", context=no_user_context
        )
        assert authenticated_user.id == user.id

    def test_change_password_with_invalid_old_password_raises_error(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test changing password with invalid old password raises AuthenticationFailedError."""
        # Create a test user
        user = user_factory(password="correctpassword")

        # Try to change password with wrong old password
        password_change = UserPasswordChange(old_password="wrongoldpassword", new_password="newpassword456")

        # The authenticate method within change_password raises AuthenticationFailedError
        with pytest.raises(AuthenticationFailedError):
            crud_users.change_password(user_id=user.id, obj_in=password_change, context=no_user_context)

    def test_change_password_with_nonexistent_user_raises_error(self, no_user_context: NoUserCtx) -> None:
        """Test changing password for non-existent user raises HTTPException."""
        # Try to change password for non-existent user
        password_change = UserPasswordChange(
            old_password="anypassword",
            new_password="newpassword456",
        )

        with pytest.raises(UserNotFoundError):
            crud_users.change_password(user_id=99999, obj_in=password_change, context=no_user_context)

    def test_reset_password_with_valid_email(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test resetting password for existing active user."""
        # Create an active test user
        user = user_factory(email="reset@example.com", is_active=True)
        original_hash = user.hashed_password

        # Reset password
        new_password = "newresetpassword123"
        reset_user = crud_users.reset_password(
            email="reset@example.com", password=new_password, context=no_user_context
        )

        assert reset_user.id == user.id
        assert reset_user.hashed_password != original_hash  # Password should be changed

        # Verify new password works
        authenticated_user = crud_users.authenticate(
            email="reset@example.com", password=new_password, context=no_user_context
        )
        assert authenticated_user.id == user.id

    def test_reset_password_with_nonexistent_email_raises_error(self, no_user_context: NoUserCtx) -> None:
        """Test resetting password for non-existent user raises UserNotFoundError."""
        with pytest.raises(UserNotFoundError):
            crud_users.reset_password(email="nonexistent@example.com", password="anypassword", context=no_user_context)

    def test_reset_password_with_inactive_user_raises_error(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test resetting password for inactive user raises InactiveUserError."""
        # Create an inactive user
        user_factory(email="inactive@example.com", is_active=False)

        with pytest.raises(InactiveUserError):
            crud_users.reset_password(email="inactive@example.com", password="anypassword", context=no_user_context)

    def test_create_if_not_exist_creates_new_user(self, no_user_context: NoUserCtx) -> None:
        """Test create_if_not_exist creates new user when not found."""
        # Create user data
        user_data = UserRegistration(
            name="New",
            surname="User",
            email="new@example.com",
            password="password123",
        )

        # Create user with filters that won't match existing users
        filters = {"email": "new@example.com"}
        created_user = crud_users.create_if_not_exist(filters=filters, obj_in=user_data, context=no_user_context)

        assert created_user.name == "New"
        assert created_user.email == "new@example.com"
        assert created_user.id is not None

    def test_create_if_not_exist_returns_existing_user(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test create_if_not_exist returns existing user when found."""
        # Create an existing user
        existing_user = user_factory(email="existing@example.com")

        # Try to create user with filters that match existing user
        user_data = UserRegistration(
            name="Duplicate",
            surname="User",
            email="different@example.com",  # Different email in data
            password="password123",
        )
        filters = {"email": "existing@example.com"}  # But filter matches existing

        returned_user = crud_users.create_if_not_exist(filters=filters, obj_in=user_data, context=no_user_context)

        # Should return existing user (not create new one)
        assert returned_user.id == existing_user.id
        assert returned_user.email == "existing@example.com"  # Original email preserved
        assert returned_user.name != "Duplicate"  # New data not used

    def test_is_active_with_active_user(self, user_factory: Callable[..., User]) -> None:
        """Test is_active returns user when user is active."""
        # Create an active user
        user = user_factory(is_active=True)

        # Check is_active
        result = crud_users.is_active(user)
        assert result.id == user.id

    def test_is_active_with_inactive_user_raises_error(self, user_factory: Callable[..., User]) -> None:
        """Test is_active raises InactiveUserError when user is inactive."""
        # Create an inactive user
        user = user_factory(is_active=False)

        # Check is_active should raise error
        with pytest.raises(InactiveUserError):
            crud_users.is_active(user)

    def test_get_permissions_for_user_without_roles(self, user_factory: Callable[..., User]) -> None:
        """Test getting permissions for user with no roles returns empty list."""
        # Create test user with no roles
        user = user_factory()

        # Get permissions (should be empty)
        user_permissions = crud_users.get_permissions(user=user)
        assert len(user_permissions) == 0

    def test_get_roles_for_user_without_roles(self, user_factory: Callable[..., User]) -> None:
        """Test getting roles for user with no roles returns empty list."""
        # Create test user with no roles
        user = user_factory()

        # Get roles (should be empty)
        user_roles = crud_users.get_roles(user=user)
        assert len(user_roles) == 0

    def test_has_permissions_for_user_without_roles(self, user_factory: Callable[..., User]) -> None:
        """Test has_permissions for user with no roles returns False."""
        # Create test user with no roles
        user = user_factory()

        # Check has_permissions (should be False)
        result = crud_users.has_permissions(user=user, permissions=["some_permission"])
        assert not result

    def test_has_roles_for_user_without_roles(self, user_factory: Callable[..., User]) -> None:
        """Test has_roles for user with no roles returns False."""
        # Create test user with no roles
        user = user_factory()

        # Check has_roles (should be False)
        result = crud_users.has_roles(user=user, roles=["some_role"])
        assert not result

    def test_get_multi_with_sort_ascending(self, no_user_context: NoUserCtx, user_factory: Callable[..., User]) -> None:
        """Test get_multi with ascending sort on name field."""
        user_factory(name="Alice", email="alice@test.com")
        user_factory(name="Bob", email="bob@test.com")
        user_factory(name="Charlie", email="charlie@test.com")

        sort_params = [("name", "asc")]
        count, sorted_users = crud_users.get_multi(sort=sort_params, context=no_user_context)

        user_names = [user.name for user in sorted_users]

        alice_idx = user_names.index("Alice")
        bob_idx = user_names.index("Bob")
        charlie_idx = user_names.index("Charlie")

        assert alice_idx < bob_idx < charlie_idx

    def test_get_multi_with_sort_descending(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test get_multi with descending sort on name field."""
        user_factory(name="Alice", email="alice2@test.com")
        user_factory(name="Bob", email="bob2@test.com")
        user_factory(name="Charlie", email="charlie2@test.com")

        sort_params = [("name", "desc")]
        count, sorted_users = crud_users.get_multi(sort=sort_params, context=no_user_context)

        user_names = [user.name for user in sorted_users]

        alice_idx = user_names.index("Alice")
        bob_idx = user_names.index("Bob")
        charlie_idx = user_names.index("Charlie")

        assert charlie_idx < bob_idx < alice_idx

    def test_get_multi_with_multi_field_sort(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test get_multi with multi-field sorting (name desc, then id asc)."""
        user_factory(name="Alice", email="alice1@test.com")
        user_factory(name="Alice", email="alice2@test.com")
        user_factory(name="Bob", email="bob1@test.com")

        sort_params = [("name", "desc"), ("id", "asc")]
        count, sorted_users = crud_users.get_multi(sort=sort_params, context=no_user_context)

        filtered_users = [u for u in sorted_users if u.name in ["Alice", "Bob"]]

        min_expected_users = 3
        alice_count = 2
        assert len(filtered_users) >= min_expected_users
        assert filtered_users[0].name == "Bob"

        alice_users = [u for u in filtered_users if u.name == "Alice"]
        assert len(alice_users) == alice_count
        assert alice_users[0].id < alice_users[1].id

    def test_get_multi_with_sort_and_pagination(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test get_multi with sorting combined with pagination."""
        user_names = ["Alpha", "Beta", "Gamma", "Delta"]
        created_users = []
        for name in user_names:
            user = user_factory(name=name, email=f"{name.lower()}@test.com")
            created_users.append(user)

        sort_params = [("name", "asc")]
        page_size = 2

        count, first_page = crud_users.get_multi(skip=0, limit=page_size, sort=sort_params, context=no_user_context)
        count, second_page = crud_users.get_multi(
            skip=page_size, limit=page_size, sort=sort_params, context=no_user_context
        )

        first_page_names = [user.name for user in first_page if user.name in user_names]
        second_page_names = [user.name for user in second_page if user.name in user_names]

        all_sorted_names = first_page_names + second_page_names
        expected_order = ["Alpha", "Beta", "Gamma", "Delta"]

        for expected_name in expected_order:
            assert expected_name in all_sorted_names

        first_expected_idx = all_sorted_names.index("Alpha")
        beta_idx = all_sorted_names.index("Beta")
        assert first_expected_idx < beta_idx

    def test_get_multi_with_sort_and_filters(
        self, no_user_context: NoUserCtx, user_factory: Callable[..., User]
    ) -> None:
        """Test get_multi with sorting combined with filters."""
        user_factory(name="ActiveA", email="activea@test.com", is_active=True)
        user_factory(name="ActiveB", email="activeb@test.com", is_active=True)
        user_factory(name="InactiveC", email="inactivec@test.com", is_active=False)

        sort_params = [("name", "desc")]
        count, filtered_sorted_users = crud_users.get_multi(sort=sort_params, is_active=True, context=no_user_context)

        active_test_users = [u for u in filtered_sorted_users if u.name.startswith("Active")]

        expected_active_count = 2
        assert len(active_test_users) == expected_active_count

        active_names = [u.name for u in active_test_users]
        assert "ActiveB" in active_names
        assert "ActiveA" in active_names

        activeb_idx = active_names.index("ActiveB")
        activea_idx = active_names.index("ActiveA")
        assert activeb_idx < activea_idx
