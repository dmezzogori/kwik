"""Tests for user CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette.status import HTTP_412_PRECONDITION_FAILED

from kwik import crud, models, schemas
from kwik.database.context_vars import current_user_ctx_var, db_conn_ctx_var
from kwik.exceptions import AuthenticationFailedError, EntityNotFoundError, InactiveUserError, UserNotFoundError
from kwik.models.user import RolePermission
from tests.utils import create_test_permission, create_test_role, create_test_user

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TestUserCRUD:
    """Test cases for user CRUD operations."""

    def _setup_context(self, db_session: Session, user: models.User | None = None) -> None:
        """Set up database session and current user context for tests."""
        db_conn_ctx_var.set(db_session)
        if user:
            current_user_ctx_var.set(user)

    def test_create_user(self, db_session: Session) -> None:
        """Test creating a new user."""
        user_data = schemas.UserRegistration(
            name="Test",
            surname="User",
            email="test@example.com",
            password="testpassword123",
            is_active=True,
            is_superuser=False,
        )

        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        created_user = crud.users.create(obj_in=user_data)

        assert created_user.name == "Test"
        assert created_user.surname == "User"
        assert created_user.email == "test@example.com"
        assert created_user.is_active is True
        assert created_user.is_superuser is False
        assert created_user.hashed_password != "testpassword123"  # Should be hashed
        assert created_user.id is not None

    def test_create_user_duplicate_email_raises_error(self, db_session: Session) -> None:
        """Test that creating a user with duplicate email raises an error."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create first user
        user_data = schemas.UserRegistration(
            name="Test1",
            surname="User1",
            email="test@example.com",
            password="testpassword123",
        )
        crud.users.create(obj_in=user_data)

        # Try to create second user with same email
        user_data2 = schemas.UserRegistration(
            name="Test2",
            surname="User2",
            email="test@example.com",  # Same email
            password="testpassword456",
        )

        with pytest.raises(IntegrityError):
            crud.users.create(obj_in=user_data2)

    def test_get_user_by_id(self, db_session: Session) -> None:
        """Test getting a user by ID."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, email="get_test@example.com")

        # Get the user by ID
        retrieved_user = crud.users.get(id=user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "get_test@example.com"

    def test_get_user_by_nonexistent_id_returns_none(self, db_session: Session) -> None:
        """Test getting a user by non-existent ID returns None."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        retrieved_user = crud.users.get(id=99999)
        assert retrieved_user is None

    def test_get_user_by_email(self, db_session: Session) -> None:
        """Test getting a user by email."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, email="email_test@example.com")

        # Get the user by email
        retrieved_user = crud.users.get_by_email(email="email_test@example.com")

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "email_test@example.com"

    def test_get_user_by_nonexistent_email_returns_none(self, db_session: Session) -> None:
        """Test getting a user by non-existent email returns None."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        retrieved_user = crud.users.get_by_email(email="nonexistent@example.com")
        assert retrieved_user is None

    def test_get_user_by_name(self, db_session: Session) -> None:
        """Test getting a user by name."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, name="uniquename")

        # Get the user by name
        retrieved_user = crud.users.get_by_name(name="uniquename")

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.name == "uniquename"

    def test_update_user(self, db_session: Session) -> None:
        """Test updating a user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, name="original")

        # Update the user
        update_data = schemas.UserProfileUpdate(name="updated")
        updated_user = crud.users.update(db_obj=user, obj_in=update_data)

        assert updated_user.id == user.id
        assert updated_user.name == "updated"
        assert updated_user.surname == user.surname  # Should remain unchanged

    def test_get_if_exist_with_existing_user(self, db_session: Session) -> None:
        """Test get_if_exist with an existing user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session)

        # Get the user using get_if_exist
        retrieved_user = crud.users.get_if_exist(id=user.id)

        assert retrieved_user.id == user.id

    def test_get_if_exist_with_nonexistent_user_raises_error(self, db_session: Session) -> None:
        """Test get_if_exist with non-existent user raises NotFound."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(EntityNotFoundError):
            crud.users.get_if_exist(id=99999)

    def test_get_multi_users(self, db_session: Session) -> None:
        """Test getting multiple users with pagination."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Test constants
        total_users = 5
        page_limit = 3
        remaining_users = 2

        # Create multiple test users
        users = []
        for i in range(total_users):
            user = create_test_user(db_session, email=f"user{i}@example.com", name=f"User{i}")
            users.append(user)

        # Get multiple users
        count, retrieved_users = crud.users.get_multi(skip=0, limit=page_limit)

        assert count == total_users  # Total count
        assert len(retrieved_users) == page_limit  # Limited to 3

        # Test pagination
        count, second_page = crud.users.get_multi(skip=page_limit, limit=page_limit)
        assert count == total_users
        assert len(second_page) == remaining_users  # Remaining users

    def test_get_multi_with_filters(self, db_session: Session) -> None:
        """Test getting multiple users with filters."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test users with different attributes
        create_test_user(db_session, email="active@example.com", is_active=True)
        create_test_user(db_session, email="inactive@example.com", is_active=False)

        # Filter by is_active
        count, active_users = crud.users.get_multi(is_active=True)
        assert count == 1
        assert active_users[0].is_active is True

        count, inactive_users = crud.users.get_multi(is_active=False)
        assert count == 1
        assert inactive_users[0].is_active is False

    def test_delete_user(self, db_session: Session) -> None:
        """Test deleting a user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session)
        user_id = user.id

        # Delete the user
        deleted_user = crud.users.delete(id=user_id)

        assert deleted_user.id == user_id

        # Verify user is deleted
        retrieved_user = crud.users.get(id=user_id)
        assert retrieved_user is None

    def test_authenticate_with_valid_credentials(self, db_session: Session) -> None:
        """Test authenticating with valid email and password."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user with known password
        password = "testpassword123"
        user = create_test_user(db_session, email="auth@example.com", password=password)

        # Authenticate with correct credentials
        authenticated_user = crud.users.authenticate(email="auth@example.com", password=password)

        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.email == "auth@example.com"

    def test_authenticate_with_invalid_email_raises_error(self, db_session: Session) -> None:
        """Test authenticating with invalid email raises AuthenticationFailedError."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(AuthenticationFailedError):
            crud.users.authenticate(email="nonexistent@example.com", password="anypassword")

    def test_authenticate_with_invalid_password_raises_error(self, db_session: Session) -> None:
        """Test authenticating with invalid password raises AuthenticationFailedError."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        create_test_user(db_session, email="auth@example.com", password="correctpassword")

        # Try to authenticate with wrong password
        with pytest.raises(AuthenticationFailedError):
            crud.users.authenticate(email="auth@example.com", password="wrongpassword")

    def test_change_password_with_valid_old_password(self, db_session: Session) -> None:
        """Test changing password with valid old password."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user with known password
        old_password = "oldpassword123"
        user = create_test_user(db_session, password=old_password)
        original_hash = user.hashed_password

        # Change password
        password_change = schemas.UserPasswordChange(old_password=old_password, new_password="newpassword456")
        updated_user = crud.users.change_password(user_id=user.id, obj_in=password_change)

        assert updated_user.id == user.id
        assert updated_user.hashed_password != original_hash  # Password should be changed

        # Verify old password no longer works
        with pytest.raises(AuthenticationFailedError):
            crud.users.authenticate(email=user.email, password=old_password)

        # Verify new password works
        authenticated_user = crud.users.authenticate(email=user.email, password="newpassword456")
        assert authenticated_user.id == user.id

    def test_change_password_with_invalid_old_password_raises_error(self, db_session: Session) -> None:
        """Test changing password with invalid old password raises AuthenticationFailedError."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, password="correctpassword")

        # Try to change password with wrong old password
        password_change = schemas.UserPasswordChange(old_password="wrongoldpassword", new_password="newpassword456")

        # The authenticate method within change_password raises AuthenticationFailedError
        with pytest.raises(AuthenticationFailedError):
            crud.users.change_password(user_id=user.id, obj_in=password_change)

    def test_change_password_with_nonexistent_user_raises_error(self, db_session: Session) -> None:
        """Test changing password for non-existent user raises HTTPException."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Try to change password for non-existent user
        password_change = schemas.UserPasswordChange(old_password="anypassword", new_password="newpassword456")

        with pytest.raises(HTTPException) as exc_info:
            crud.users.change_password(user_id=99999, obj_in=password_change)

        assert exc_info.value.status_code == HTTP_412_PRECONDITION_FAILED
        assert "does not exist" in exc_info.value.detail

    def test_reset_password_with_valid_email(self, db_session: Session) -> None:
        """Test resetting password for existing active user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create an active test user
        user = create_test_user(db_session, email="reset@example.com", is_active=True)
        original_hash = user.hashed_password

        # Reset password
        new_password = "newresetpassword123"
        reset_user = crud.users.reset_password(email="reset@example.com", password=new_password)

        assert reset_user.id == user.id
        assert reset_user.hashed_password != original_hash  # Password should be changed

        # Verify new password works
        authenticated_user = crud.users.authenticate(email="reset@example.com", password=new_password)
        assert authenticated_user.id == user.id

    def test_reset_password_with_nonexistent_email_raises_error(self, db_session: Session) -> None:
        """Test resetting password for non-existent user raises UserNotFoundError."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(UserNotFoundError):
            crud.users.reset_password(email="nonexistent@example.com", password="anypassword")

    def test_reset_password_with_inactive_user_raises_error(self, db_session: Session) -> None:
        """Test resetting password for inactive user raises InactiveUserError."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create an inactive user
        create_test_user(db_session, email="inactive@example.com", is_active=False)

        with pytest.raises(InactiveUserError):
            crud.users.reset_password(email="inactive@example.com", password="anypassword")

    def test_create_if_not_exist_creates_new_user(self, db_session: Session) -> None:
        """Test create_if_not_exist creates new user when not found."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create user data
        user_data = schemas.UserRegistration(
            name="New", surname="User", email="new@example.com", password="password123"
        )

        # Create user with filters that won't match existing users
        filters = {"email": "new@example.com"}
        created_user = crud.users.create_if_not_exist(filters=filters, obj_in=user_data)

        assert created_user.name == "New"
        assert created_user.email == "new@example.com"
        assert created_user.id is not None

    def test_create_if_not_exist_returns_existing_user(self, db_session: Session) -> None:
        """Test create_if_not_exist returns existing user when found."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create an existing user
        existing_user = create_test_user(db_session, email="existing@example.com")

        # Try to create user with filters that match existing user
        user_data = schemas.UserRegistration(
            name="Duplicate",
            surname="User",
            email="different@example.com",  # Different email in data
            password="password123",
        )
        filters = {"email": "existing@example.com"}  # But filter matches existing

        returned_user = crud.users.create_if_not_exist(filters=filters, obj_in=user_data)

        # Should return existing user (not create new one)
        assert returned_user.id == existing_user.id
        assert returned_user.email == "existing@example.com"  # Original email preserved
        assert returned_user.name != "Duplicate"  # New data not used

    def test_is_active_with_active_user(self, db_session: Session) -> None:
        """Test is_active returns user when user is active."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create an active user
        user = create_test_user(db_session, is_active=True)

        # Check is_active
        result = crud.users.is_active(user)
        assert result.id == user.id

    def test_is_active_with_inactive_user_raises_error(self, db_session: Session) -> None:
        """Test is_active raises InactiveUserError when user is inactive."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create an inactive user
        user = create_test_user(db_session, is_active=False)

        # Check is_active should raise error
        with pytest.raises(InactiveUserError):
            crud.users.is_active(user)

    def test_is_superuser_with_superuser(self, db_session: Session) -> None:
        """Test is_superuser returns True for superuser."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a superuser
        user = create_test_user(db_session, is_superuser=True)

        # Check is_superuser
        result = crud.users.is_superuser(user_id=user.id)
        assert result is True

    def test_is_superuser_with_regular_user(self, db_session: Session) -> None:
        """Test is_superuser returns False for regular user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a regular user
        user = create_test_user(db_session, is_superuser=False)

        # Check is_superuser
        result = crud.users.is_superuser(user_id=user.id)
        assert result is False

    def test_is_superuser_with_nonexistent_user_raises_error(self, db_session: Session) -> None:
        """Test is_superuser raises EntityNotFoundError for non-existent user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(EntityNotFoundError):
            crud.users.is_superuser(user_id=99999)

    def test_assign_role_to_user(self, db_session: Session) -> None:
        """Test assigning a role to a user."""
        # Create test user and set context
        user = create_test_user(db_session)
        self._setup_context(db_session, user)

        # Create test role
        role = create_test_role(db_session, name="test_role", creator_user_id=user.id)

        # Assign role to user
        result_user = crud.users.assign_role(user_id=user.id, role_id=role.id)

        assert result_user.id == user.id

        # Verify user has the role
        has_role = crud.users.has_roles(user_id=user.id, roles=["test_role"])
        assert has_role is True

    def test_assign_role_idempotent_operation(self, db_session: Session) -> None:
        """Test that assigning same role twice is idempotent."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user and role
        user = create_test_user(db_session)
        role = create_test_role(db_session, name="test_role", creator_user_id=user.id)

        # Assign role twice
        crud.users.assign_role(user_id=user.id, role_id=role.id)
        result_user = crud.users.assign_role(user_id=user.id, role_id=role.id)

        assert result_user.id == user.id
        # Should still work without error (idempotent)

    def test_assign_role_with_nonexistent_user_raises_error(self, db_session: Session) -> None:
        """Test assigning role to non-existent user raises EntityNotFoundError."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test role
        user = create_test_user(db_session)  # Need user for role creation
        role = create_test_role(db_session, creator_user_id=user.id)

        with pytest.raises(EntityNotFoundError):
            crud.users.assign_role(user_id=99999, role_id=role.id)

    def test_remove_role_from_user(self, db_session: Session) -> None:
        """Test removing a role from a user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user and role
        user = create_test_user(db_session)
        role = create_test_role(db_session, name="test_role", creator_user_id=user.id)

        # Assign then remove role
        crud.users.assign_role(user_id=user.id, role_id=role.id)
        result_user = crud.users.remove_role(user_id=user.id, role_id=role.id)

        assert result_user.id == user.id

        # Verify user no longer has the role
        has_role = crud.users.has_roles(user_id=user.id, roles=["test_role"])
        assert has_role is False

    def test_remove_role_idempotent_operation(self, db_session: Session) -> None:
        """Test that removing non-assigned role is idempotent."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user and role
        user = create_test_user(db_session)
        role = create_test_role(db_session, creator_user_id=user.id)

        # Remove role that was never assigned (should not raise error)
        result_user = crud.users.remove_role(user_id=user.id, role_id=role.id)
        assert result_user.id == user.id

    def test_has_roles_with_assigned_roles(self, db_session: Session) -> None:
        """Test has_roles returns True when user has all specified roles."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user and roles
        user = create_test_user(db_session)
        role1 = create_test_role(db_session, name="role1", creator_user_id=user.id)
        role2 = create_test_role(db_session, name="role2", creator_user_id=user.id)

        # Assign both roles
        crud.users.assign_role(user_id=user.id, role_id=role1.id)
        crud.users.assign_role(user_id=user.id, role_id=role2.id)

        # Check if user has both roles
        has_both = crud.users.has_roles(user_id=user.id, roles=["role1", "role2"])
        assert has_both is True

        # Check if user has one role
        has_one = crud.users.has_roles(user_id=user.id, roles=["role1"])
        assert has_one is True

    def test_has_roles_with_missing_roles(self, db_session: Session) -> None:
        """Test has_roles returns False when user missing some roles."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user and role
        user = create_test_user(db_session)
        role1 = create_test_role(db_session, name="role1", creator_user_id=user.id)

        # Assign only one role
        crud.users.assign_role(user_id=user.id, role_id=role1.id)

        # Check if user has both roles (should be False)
        has_both = crud.users.has_roles(user_id=user.id, roles=["role1", "nonexistent_role"])
        assert has_both is False

    def test_get_multi_by_role_name(self, db_session: Session) -> None:
        """Test getting users by role name."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test users and role
        user1 = create_test_user(db_session, email="user1@example.com")
        user2 = create_test_user(db_session, email="user2@example.com")
        user3 = create_test_user(db_session, email="user3@example.com")
        role = create_test_role(db_session, name="target_role", creator_user_id=user1.id)

        # Assign role to only user1 and user2
        crud.users.assign_role(user_id=user1.id, role_id=role.id)
        crud.users.assign_role(user_id=user2.id, role_id=role.id)

        # Get users by role name
        users_with_role = crud.users.get_multi_by_role_name(role_name="target_role")

        expected_number_of_users_with_role = 2
        assert len(users_with_role) == expected_number_of_users_with_role
        user_ids = {user.id for user in users_with_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        assert user3.id not in user_ids

    def test_get_multi_by_role_id(self, db_session: Session) -> None:
        """Test getting users by role ID."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test users and role
        user1 = create_test_user(db_session, email="user1@example.com")
        user2 = create_test_user(db_session, email="user2@example.com")
        user3 = create_test_user(db_session, email="user3@example.com")
        role = create_test_role(db_session, name="target_role", creator_user_id=user1.id)

        # Assign role to only user1 and user2
        crud.users.assign_role(user_id=user1.id, role_id=role.id)
        crud.users.assign_role(user_id=user2.id, role_id=role.id)

        # Get users by role ID
        users_with_role = crud.users.get_multi_by_role_id(role_id=role.id)

        expected_number_of_users_with_role = 2
        assert len(users_with_role) == expected_number_of_users_with_role
        user_ids = {user.id for user in users_with_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        assert user3.id not in user_ids

    def test_has_permissions_with_assigned_permissions(self, db_session: Session) -> None:
        """Test has_permissions returns True when user has all specified permissions through roles."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user, role, and permissions
        user = create_test_user(db_session)
        role = create_test_role(db_session, name="test_role", creator_user_id=user.id)
        perm1 = create_test_permission(db_session, name="permission1", creator_user_id=user.id)
        perm2 = create_test_permission(db_session, name="permission2", creator_user_id=user.id)

        # Associate permissions with role
        role_perm1 = RolePermission(role_id=role.id, permission_id=perm1.id, creator_user_id=user.id)
        role_perm2 = RolePermission(role_id=role.id, permission_id=perm2.id, creator_user_id=user.id)
        db_session.add(role_perm1)
        db_session.add(role_perm2)
        db_session.commit()

        # Assign role to user
        crud.users.assign_role(user_id=user.id, role_id=role.id)

        # Check if user has both permissions
        has_both = crud.users.has_permissions(user_id=user.id, permissions=["permission1", "permission2"])
        assert has_both is True

        # Check if user has one permission
        has_one = crud.users.has_permissions(user_id=user.id, permissions=["permission1"])
        assert has_one is True

    def test_has_permissions_with_missing_permissions(self, db_session: Session) -> None:
        """Test has_permissions returns False when user missing some permissions."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user, role, and permission
        user = create_test_user(db_session)
        role = create_test_role(db_session, name="test_role", creator_user_id=user.id)
        perm1 = create_test_permission(db_session, name="permission1", creator_user_id=user.id)

        # Associate only one permission with role
        role_perm1 = RolePermission(role_id=role.id, permission_id=perm1.id, creator_user_id=user.id)
        db_session.add(role_perm1)
        db_session.commit()

        # Assign role to user
        crud.users.assign_role(user_id=user.id, role_id=role.id)

        # Check if user has both permissions (should be False)
        has_both = crud.users.has_permissions(user_id=user.id, permissions=["permission1", "nonexistent_permission"])
        assert has_both is False

    def test_get_permissions_for_user(self, db_session: Session) -> None:
        """Test getting all permissions for a user through their roles."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user, roles, and permissions
        user = create_test_user(db_session)
        role1 = create_test_role(db_session, name="role1", creator_user_id=user.id)
        role2 = create_test_role(db_session, name="role2", creator_user_id=user.id)
        perm1 = create_test_permission(db_session, name="permission1", creator_user_id=user.id)
        perm2 = create_test_permission(db_session, name="permission2", creator_user_id=user.id)
        perm3 = create_test_permission(db_session, name="permission3", creator_user_id=user.id)

        # Associate permissions with roles
        role1_perm1 = RolePermission(role_id=role1.id, permission_id=perm1.id, creator_user_id=user.id)
        role1_perm2 = RolePermission(role_id=role1.id, permission_id=perm2.id, creator_user_id=user.id)
        role2_perm2 = RolePermission(
            role_id=role2.id, permission_id=perm2.id, creator_user_id=user.id
        )  # Overlapping permission
        role2_perm3 = RolePermission(role_id=role2.id, permission_id=perm3.id, creator_user_id=user.id)

        db_session.add_all([role1_perm1, role1_perm2, role2_perm2, role2_perm3])
        db_session.commit()

        # Assign both roles to user
        crud.users.assign_role(user_id=user.id, role_id=role1.id)
        crud.users.assign_role(user_id=user.id, role_id=role2.id)

        # Get all permissions for user
        user_permissions = crud.users.get_permissions(user_id=user.id)

        # Should get distinct permissions (perm2 should appear only once despite being in both roles)
        permission_names = {perm.name for perm in user_permissions}
        expected_number_of_permissions = 3  # perm1, perm2, perm3
        assert len(permission_names) == expected_number_of_permissions
        assert "permission1" in permission_names
        assert "permission2" in permission_names
        assert "permission3" in permission_names

    def test_get_permissions_for_user_without_roles(self, db_session: Session) -> None:
        """Test getting permissions for user with no roles returns empty list."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test user with no roles
        user = create_test_user(db_session)

        # Get permissions (should be empty)
        user_permissions = crud.users.get_permissions(user_id=user.id)
        assert len(user_permissions) == 0
