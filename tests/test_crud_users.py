"""Tests for user CRUD operations."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from kwik import schemas
from kwik.crud import crud_users
from kwik.exceptions import AuthenticationFailedError, EntityNotFoundError, InactiveUserError, UserNotFoundError
from tests.utils import create_test_user


class TestUserCRUD:
    """Test cases for user CRUD operations."""

    def test_create_user(self) -> None:
        """Test creating a new user."""
        created_user = create_test_user(
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

    def test_create_user_duplicate_email_raises_error(self) -> None:
        """Test that creating a user with duplicate email raises an error."""
        # Create first user
        user_data = schemas.UserRegistration(
            name="Test1",
            surname="User1",
            email="test@example.com",
            password="testpassword123",
        )
        crud_users.create(obj_in=user_data)

        # Try to create second user with same email
        with pytest.raises(IntegrityError):
            crud_users.create(obj_in=user_data)

    def test_get_user_by_id(self) -> None:
        """Test getting a user by ID."""
        # Create a test user
        user = create_test_user()

        # Get the user by ID
        retrieved_user = crud_users.get(id=user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email

    def test_get_user_by_nonexistent_id_returns_none(self) -> None:
        """Test getting a user by non-existent ID returns None."""
        retrieved_user = crud_users.get(id=99999)
        assert retrieved_user is None

        with pytest.raises(EntityNotFoundError):
            crud_users.get_if_exist(id=99999)

    def test_get_user_by_email(self) -> None:
        """Test getting a user by email."""
        # Create a test user
        user = create_test_user()

        # Get the user by email
        retrieved_user = crud_users.get_by_email(email=user.email)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email

    def test_get_user_by_nonexistent_email_returns_none(self) -> None:
        """Test getting a user by non-existent email returns None."""
        retrieved_user = crud_users.get_by_email(email="nonexistent@example.com")
        assert retrieved_user is None

    def test_update_user(self) -> None:
        """Test updating a user."""
        # Create a test user
        user = create_test_user()

        # Update the user
        update_data = schemas.UserProfileUpdate(
            name="updated_name",
            surname="updated_surname",
            email="updated@example.com",
            is_active=False,
        )
        updated_user = crud_users.update(db_obj=user, obj_in=update_data)

        assert updated_user.id == user.id
        assert updated_user.name == "updated_name"
        assert updated_user.surname == "updated_surname"
        assert updated_user.email == "updated@example.com"
        assert updated_user.is_active is False

    def test_update_user_password_incorrectly(self) -> None:
        """Test updating a user with an incorrect password."""
        # Create a test user
        user = create_test_user()

        # Attempt to update the user with an incorrect password
        with pytest.raises(ValidationError):
            crud_users.update(db_obj=user, obj_in=schemas.UserProfileUpdate(password="newpassword123"))

    def test_get_if_exist_with_existing_user(self) -> None:
        """Test get_if_exist with an existing user."""
        # Create a test user
        user = create_test_user()

        # Get the user using get_if_exist
        retrieved_user = crud_users.get_if_exist(id=user.id)

        assert retrieved_user.id == user.id

    def test_get_if_exist_with_nonexistent_user_raises_error(self) -> None:
        """Test get_if_exist with non-existent user raises NotFound."""
        with pytest.raises(EntityNotFoundError):
            crud_users.get_if_exist(id=99999)

    def test_get_multi_users(self) -> None:
        """Test getting multiple users with pagination."""
        # Test constants
        total_users = 5
        page_limit = 3
        remaining_users = 2

        # Create multiple test users
        users = []
        for i in range(total_users):
            user = create_test_user(email=f"user{i}@example.com", name=f"User{i}")
            users.append(user)

        # Get multiple users
        count, retrieved_users = crud_users.get_multi(skip=0, limit=page_limit)

        assert count == total_users  # Total count
        assert len(retrieved_users) == page_limit  # Limited to 3

        # Test pagination
        count, second_page = crud_users.get_multi(skip=page_limit, limit=page_limit)
        assert count == total_users
        assert len(second_page) == remaining_users  # Remaining users

    def test_get_multi_with_filters(self) -> None:
        """Test getting multiple users with filters."""
        # Create test users with different attributes
        create_test_user(email="active@example.com", is_active=True)
        create_test_user(email="inactive@example.com", is_active=False)

        # Filter by is_active
        count, active_users = crud_users.get_multi(is_active=True)
        assert count == 1
        assert active_users[0].is_active is True

        count, inactive_users = crud_users.get_multi(is_active=False)
        assert count == 1
        assert inactive_users[0].is_active is False

    def test_delete_user(self) -> None:
        """Test deleting a user."""
        # Create a test user
        user = create_test_user()
        user_id = user.id

        # Delete the user
        deleted_user = crud_users.delete(id=user_id)

        assert deleted_user.id == user_id

        # Verify user is deleted
        retrieved_user = crud_users.get(id=user_id)
        assert retrieved_user is None

    def test_authenticate_with_valid_credentials(self) -> None:
        """Test authenticating with valid email and password."""
        # Create a test user with known password
        password = "testpassword123"
        user = create_test_user(email="auth@example.com", password=password)

        # Authenticate with correct credentials
        authenticated_user = crud_users.authenticate(email="auth@example.com", password=password)

        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.email == "auth@example.com"

    def test_authenticate_with_invalid_email_raises_error(self) -> None:
        """Test authenticating with invalid email raises AuthenticationFailedError."""
        with pytest.raises(AuthenticationFailedError):
            crud_users.authenticate(email="nonexistent@example.com", password="anypassword")

    def test_authenticate_with_invalid_password_raises_error(self) -> None:
        """Test authenticating with invalid password raises AuthenticationFailedError."""
        # Create a test user
        create_test_user(email="auth@example.com", password="correctpassword")

        # Try to authenticate with wrong password
        with pytest.raises(AuthenticationFailedError):
            crud_users.authenticate(email="auth@example.com", password="wrongpassword")

    def test_change_password_with_valid_old_password(self) -> None:
        """Test changing password with valid old password."""
        # Create a test user with known password
        old_password = "oldpassword123"
        user = create_test_user(password=old_password)
        original_hash = user.hashed_password

        # Change password
        password_change = schemas.UserPasswordChange(old_password=old_password, new_password="newpassword456")
        updated_user = crud_users.change_password(user_id=user.id, obj_in=password_change)

        assert updated_user.id == user.id
        assert updated_user.hashed_password != original_hash  # Password should be changed

        # Verify old password no longer works
        with pytest.raises(AuthenticationFailedError):
            crud_users.authenticate(email=user.email, password=old_password)

        # Verify new password works
        authenticated_user = crud_users.authenticate(email=user.email, password="newpassword456")
        assert authenticated_user.id == user.id

    def test_change_password_with_invalid_old_password_raises_error(self) -> None:
        """Test changing password with invalid old password raises AuthenticationFailedError."""
        # Create a test user
        user = create_test_user(password="correctpassword")

        # Try to change password with wrong old password
        password_change = schemas.UserPasswordChange(old_password="wrongoldpassword", new_password="newpassword456")

        # The authenticate method within change_password raises AuthenticationFailedError
        with pytest.raises(AuthenticationFailedError):
            crud_users.change_password(user_id=user.id, obj_in=password_change)

    def test_change_password_with_nonexistent_user_raises_error(self) -> None:
        """Test changing password for non-existent user raises HTTPException."""
        # Try to change password for non-existent user
        password_change = schemas.UserPasswordChange(old_password="anypassword", new_password="newpassword456")

        with pytest.raises(UserNotFoundError):
            crud_users.change_password(user_id=99999, obj_in=password_change)

    def test_reset_password_with_valid_email(self) -> None:
        """Test resetting password for existing active user."""
        # Create an active test user
        user = create_test_user(email="reset@example.com", is_active=True)
        original_hash = user.hashed_password

        # Reset password
        new_password = "newresetpassword123"
        reset_user = crud_users.reset_password(email="reset@example.com", password=new_password)

        assert reset_user.id == user.id
        assert reset_user.hashed_password != original_hash  # Password should be changed

        # Verify new password works
        authenticated_user = crud_users.authenticate(email="reset@example.com", password=new_password)
        assert authenticated_user.id == user.id

    def test_reset_password_with_nonexistent_email_raises_error(self) -> None:
        """Test resetting password for non-existent user raises UserNotFoundError."""
        with pytest.raises(UserNotFoundError):
            crud_users.reset_password(email="nonexistent@example.com", password="anypassword")

    def test_reset_password_with_inactive_user_raises_error(self) -> None:
        """Test resetting password for inactive user raises InactiveUserError."""
        # Create an inactive user
        create_test_user(email="inactive@example.com", is_active=False)

        with pytest.raises(InactiveUserError):
            crud_users.reset_password(email="inactive@example.com", password="anypassword")

    def test_create_if_not_exist_creates_new_user(self) -> None:
        """Test create_if_not_exist creates new user when not found."""
        # Create user data
        user_data = schemas.UserRegistration(
            name="New", surname="User", email="new@example.com", password="password123"
        )

        # Create user with filters that won't match existing users
        filters = {"email": "new@example.com"}
        created_user = crud_users.create_if_not_exist(filters=filters, obj_in=user_data)

        assert created_user.name == "New"
        assert created_user.email == "new@example.com"
        assert created_user.id is not None

    def test_create_if_not_exist_returns_existing_user(self) -> None:
        """Test create_if_not_exist returns existing user when found."""
        # Create an existing user
        existing_user = create_test_user(email="existing@example.com")

        # Try to create user with filters that match existing user
        user_data = schemas.UserRegistration(
            name="Duplicate",
            surname="User",
            email="different@example.com",  # Different email in data
            password="password123",
        )
        filters = {"email": "existing@example.com"}  # But filter matches existing

        returned_user = crud_users.create_if_not_exist(filters=filters, obj_in=user_data)

        # Should return existing user (not create new one)
        assert returned_user.id == existing_user.id
        assert returned_user.email == "existing@example.com"  # Original email preserved
        assert returned_user.name != "Duplicate"  # New data not used

    def test_is_active_with_active_user(self) -> None:
        """Test is_active returns user when user is active."""
        # Create an active user
        user = create_test_user(is_active=True)

        # Check is_active
        result = crud_users.is_active(user)
        assert result.id == user.id

    def test_is_active_with_inactive_user_raises_error(self) -> None:
        """Test is_active raises InactiveUserError when user is inactive."""
        # Create an inactive user
        user = create_test_user(is_active=False)

        # Check is_active should raise error
        with pytest.raises(InactiveUserError):
            crud_users.is_active(user)

    def test_get_permissions_for_user_without_roles(self) -> None:
        """Test getting permissions for user with no roles returns empty list."""
        # Create test user with no roles
        user = create_test_user()

        # Get permissions (should be empty)
        user_permissions = crud_users.get_permissions(user=user)
        assert len(user_permissions) == 0

    def test_get_roles_for_user_without_roles(self) -> None:
        """Test getting roles for user with no roles returns empty list."""
        # Create test user with no roles
        user = create_test_user()

        # Get roles (should be empty)
        user_roles = crud_users.get_roles(user=user)
        assert len(user_roles) == 0

    def test_has_permissions_for_user_without_roles(self) -> None:
        """Test has_permissions for user with no roles returns False."""
        # Create test user with no roles
        user = create_test_user()

        # Check has_permissions (should be False)
        result = crud_users.has_permissions(user=user, permissions=["some_permission"])
        assert not result

    def test_has_roles_for_user_without_roles(self) -> None:
        """Test has_roles for user with no roles returns False."""
        # Create test user with no roles
        user = create_test_user()

        # Check has_roles (should be False)
        result = crud_users.has_roles(user=user, roles=["some_role"])
        assert not result
