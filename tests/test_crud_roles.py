"""Tests for role CRUD operations."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

import pytest

from kwik import crud, schemas
from kwik.database.context_vars import db_conn_ctx_var
from kwik.exceptions import NotFound
from tests.utils import create_test_role

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@pytest.mark.skip(reason="Roles endpoint temporarily disabled")
class TestRoleCRUD:
    """Test cases for role CRUD operations."""

    def test_create_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test creating a new role."""
        role_data = schemas.RoleDefinition(
            name="Test Role",
            is_active=True,
            is_locked=False,
        )

        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        created_role = crud.roles.create(obj_in=role_data)

        assert created_role.name == "Test Role"
        assert created_role.is_active is True
        assert created_role.is_locked is False
        assert created_role.id is not None

    def test_get_role_by_id(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting a role by ID."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(db_session, name="Get Test Role")

        # Get the role by ID
        retrieved_role = crud.roles.get(id=role.id)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == "Get Test Role"

    def test_get_role_by_nonexistent_id_returns_none(self, db_session: Session) -> None:
        """Test getting a role by non-existent ID returns None."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        retrieved_role = crud.roles.get(id=99999)
        assert retrieved_role is None

    def test_update_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test updating a role."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(db_session, name="Original Role")

        # Update the role
        update_data = schemas.RoleUpdate(name="Updated Role")
        updated_role = crud.roles.update(db_obj=role, obj_in=update_data)

        assert updated_role.id == role.id
        assert updated_role.name == "Updated Role"
        assert updated_role.is_active == role.is_active  # Should remain unchanged

    def test_get_if_exist_with_existing_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test get_if_exist with an existing role."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(db_session)

        # Get the role using get_if_exist
        retrieved_role = crud.roles.get_if_exist(id=role.id)

        assert retrieved_role.id == role.id

    def test_get_if_exist_with_nonexistent_role_raises_error(self, db_session: Session) -> None:
        """Test get_if_exist with non-existent role raises NotFound."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(NotFound):
            crud.roles.get_if_exist(id=99999)

    def test_get_multi_roles(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting multiple roles with pagination."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Test constants
        TOTAL_ROLES = 5
        PAGE_LIMIT = 3
        REMAINING_ROLES = 2

        # Create multiple test roles
        roles = []
        for i in range(TOTAL_ROLES):
            role = create_test_role(db_session, name=f"Role {i}")
            roles.append(role)

        # Get multiple roles
        count, retrieved_roles = crud.roles.get_multi(skip=0, limit=PAGE_LIMIT)

        assert count == TOTAL_ROLES  # Total count
        assert len(retrieved_roles) == PAGE_LIMIT  # Limited to 3

        # Test pagination
        count, second_page = crud.roles.get_multi(skip=PAGE_LIMIT, limit=PAGE_LIMIT)
        assert count == TOTAL_ROLES
        assert len(second_page) == REMAINING_ROLES  # Remaining roles

    def test_get_multi_with_filters(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting multiple roles with filters."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test roles with different attributes
        create_test_role(db_session, name="Active Role", is_active=True)
        create_test_role(db_session, name="Inactive Role", is_active=False)
        create_test_role(db_session, name="Locked Role", is_locked=True)

        # Filter by is_active
        count, active_roles = crud.roles.get_multi(is_active=True)
        EXPECTED_ACTIVE_ROLES = 2  # Active Role and Locked Role
        assert count == EXPECTED_ACTIVE_ROLES

        count, inactive_roles = crud.roles.get_multi(is_active=False)
        assert count == 1
        assert inactive_roles[0].name == "Inactive Role"

        # Filter by is_locked
        count, locked_roles = crud.roles.get_multi(is_locked=True)
        assert count == 1
        assert locked_roles[0].name == "Locked Role"

    def test_delete_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test deleting a role (hard delete)."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(db_session, name="To Delete")
        role_id = role.id

        # Delete the role (hard delete)
        deleted_role = crud.roles.delete(id=role_id)

        assert deleted_role.id == role_id

        # Verify role is completely removed
        retrieved_role = crud.roles.get(id=role_id)
        assert retrieved_role is None  # Should not be found after deletion

    def test_get_all_roles(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting all roles."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test roles
        create_test_role(db_session, name="Role 1")
        create_test_role(db_session, name="Role 2")
        create_test_role(db_session, name="Role 3")

        # Get all roles
        all_roles = crud.roles.get_all()

        EXPECTED_TOTAL_ROLES = 3
        assert len(all_roles) == EXPECTED_TOTAL_ROLES
        role_names = [role.name for role in all_roles]
        assert "Role 1" in role_names
        assert "Role 2" in role_names
        assert "Role 3" in role_names
