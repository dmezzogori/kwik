"""Tests for user CRUD operations."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from kwik import crud, schemas
from kwik.database.context_vars import db_conn_ctx_var
from kwik.exceptions import NotFound
from kwik.models.user import User
from tests.utils import create_test_user, cleanup_database


class TestUserCRUD:
    """Test cases for user CRUD operations."""

    def test_create_user(self, db_session, clean_db) -> None:
        """Test creating a new user."""
        user_data = schemas.UserCreateSchema(
            name="Test",
            surname="User",
            email="test@example.com",
            password="testpassword123",
            is_active=True,
            is_superuser=False,
        )

        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        created_user = crud.user.create(obj_in=user_data)

        assert created_user.name == "Test"
        assert created_user.surname == "User"
        assert created_user.email == "test@example.com"
        assert created_user.is_active is True
        assert created_user.is_superuser is False
        assert created_user.hashed_password != "testpassword123"  # Should be hashed
        assert created_user.id is not None

    def test_create_user_duplicate_email_raises_error(self, db_session, clean_db) -> None:
        """Test that creating a user with duplicate email raises an error."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create first user
        user_data = schemas.UserCreateSchema(
            name="Test1",
            surname="User1",
            email="test@example.com",
            password="testpassword123",
        )
        crud.user.create(obj_in=user_data)

        # Try to create second user with same email
        user_data2 = schemas.UserCreateSchema(
            name="Test2",
            surname="User2",
            email="test@example.com",  # Same email
            password="testpassword456",
        )

        with pytest.raises(IntegrityError):
            crud.user.create(obj_in=user_data2)

    def test_get_user_by_id(self, db_session, clean_db) -> None:
        """Test getting a user by ID."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, email="get_test@example.com")

        # Get the user by ID
        retrieved_user = crud.user.get(id=user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "get_test@example.com"

    def test_get_user_by_nonexistent_id_returns_none(self, db_session, clean_db) -> None:
        """Test getting a user by non-existent ID returns None."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        retrieved_user = crud.user.get(id=99999)
        assert retrieved_user is None

    def test_get_user_by_email(self, db_session, clean_db) -> None:
        """Test getting a user by email."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, email="email_test@example.com")

        # Get the user by email
        retrieved_user = crud.user.get_by_email(email="email_test@example.com")

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "email_test@example.com"

    def test_get_user_by_nonexistent_email_returns_none(self, db_session, clean_db) -> None:
        """Test getting a user by non-existent email returns None."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        retrieved_user = crud.user.get_by_email(email="nonexistent@example.com")
        assert retrieved_user is None

    def test_get_user_by_name(self, db_session, clean_db) -> None:
        """Test getting a user by name."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, name="uniquename")

        # Get the user by name
        retrieved_user = crud.user.get_by_name(name="uniquename")

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.name == "uniquename"

    def test_update_user(self, db_session, clean_db) -> None:
        """Test updating a user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session, name="original")

        # Update the user
        update_data = schemas.UserUpdateSchema(name="updated")
        updated_user = crud.user.update(db_obj=user, obj_in=update_data)

        assert updated_user.id == user.id
        assert updated_user.name == "updated"
        assert updated_user.surname == user.surname  # Should remain unchanged

    def test_get_if_exist_with_existing_user(self, db_session, clean_db) -> None:
        """Test get_if_exist with an existing user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session)

        # Get the user using get_if_exist
        retrieved_user = crud.user.get_if_exist(id=user.id)

        assert retrieved_user.id == user.id

    def test_get_if_exist_with_nonexistent_user_raises_error(self, db_session, clean_db) -> None:
        """Test get_if_exist with non-existent user raises NotFound."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(NotFound):
            crud.user.get_if_exist(id=99999)

    def test_get_multi_users(self, db_session, clean_db) -> None:
        """Test getting multiple users with pagination."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create multiple test users
        users = []
        for i in range(5):
            user = create_test_user(db_session, email=f"user{i}@example.com", name=f"User{i}")
            users.append(user)

        # Get multiple users
        count, retrieved_users = crud.user.get_multi(skip=0, limit=3)

        assert count == 5  # Total count
        assert len(retrieved_users) == 3  # Limited to 3

        # Test pagination
        count, second_page = crud.user.get_multi(skip=3, limit=3)
        assert count == 5
        assert len(second_page) == 2  # Remaining users

    def test_get_multi_with_filters(self, db_session, clean_db) -> None:
        """Test getting multiple users with filters."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test users with different attributes
        create_test_user(db_session, email="active@example.com", is_active=True)
        create_test_user(db_session, email="inactive@example.com", is_active=False)

        # Filter by is_active
        count, active_users = crud.user.get_multi(is_active=True)
        assert count == 1
        assert active_users[0].is_active is True

        count, inactive_users = crud.user.get_multi(is_active=False)
        assert count == 1
        assert inactive_users[0].is_active is False

    def test_delete_user(self, db_session, clean_db) -> None:
        """Test deleting a user."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test user
        user = create_test_user(db_session)
        user_id = user.id

        # Delete the user
        deleted_user = crud.user.delete(id=user_id)

        assert deleted_user.id == user_id

        # Verify user is deleted
        retrieved_user = crud.user.get(id=user_id)
        assert retrieved_user is None
