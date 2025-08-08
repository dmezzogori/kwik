"""Tests for role CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik import crud, schemas
from kwik.database.context_vars import db_conn_ctx_var
from kwik.exceptions import EntityNotFoundError
from tests.utils import create_test_role

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import Session


class TestRoleCRUD:
    """Test cases for role CRUD operations."""

    def test_create_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test creating a new role."""
        role_data = schemas.RoleDefinition(name="Test Role", is_active=True)

        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        created_role = crud.crud_roles.create(obj_in=role_data)

        assert created_role.name == "Test Role"
        assert created_role.is_active is True
        assert created_role.id is not None

    def test_get_role_by_id(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting a role by ID."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(name="Get Test Role")

        # Get the role by ID
        retrieved_role = crud.crud_roles.get(id=role.id)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == "Get Test Role"

    def test_get_role_by_nonexistent_id_returns_none(self, db_session: Session) -> None:
        """Test getting a role by non-existent ID returns None."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        retrieved_role = crud.crud_roles.get(id=99999)
        assert retrieved_role is None

    def test_update_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test updating a role."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(name="Original Role")

        # Update the role
        update_data = schemas.RoleUpdate(name="Updated Role")
        updated_role = crud.crud_roles.update(db_obj=role, obj_in=update_data)

        assert updated_role.id == role.id
        assert updated_role.name == "Updated Role"
        assert updated_role.is_active == role.is_active  # Should remain unchanged

    def test_get_if_exist_with_existing_role(
        self,
        db_session: Session,
        user_context: Generator[None, None, None],  # noqa: ARG002
    ) -> None:
        """Test get_if_exist with an existing role."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role()

        # Get the role using get_if_exist
        retrieved_role = crud.crud_roles.get_if_exist(id=role.id)

        assert retrieved_role.id == role.id

    def test_get_if_exist_with_nonexistent_role_raises_error(self, db_session: Session) -> None:
        """Test get_if_exist with non-existent role raises NotFound."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        with pytest.raises(EntityNotFoundError):
            crud.crud_roles.get_if_exist(id=99999)

    def test_get_multi_roles(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting multiple roles with pagination."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Test constants
        total_roles = 5
        page_limit = 3
        remaining_roles = 2

        # Create multiple test roles
        roles = []
        for i in range(total_roles):
            role = create_test_role(name=f"Role {i}")
            roles.append(role)

        # Get multiple roles
        count, retrieved_roles = crud.crud_roles.get_multi(skip=0, limit=page_limit)

        assert count == total_roles  # Total count
        assert len(retrieved_roles) == page_limit  # Limited to 3

        # Test pagination
        count, second_page = crud.crud_roles.get_multi(skip=page_limit, limit=page_limit)
        assert count == total_roles
        assert len(second_page) == remaining_roles  # Remaining roles

    def test_get_multi_with_filters(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test getting multiple roles with filters."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create test roles with different attributes
        create_test_role(name="Active Role", is_active=True)
        create_test_role(db_session, name="Inactive Role", is_active=False)

        # Filter by is_active
        count, active_roles = crud.crud_roles.get_multi(is_active=True)
        expected_active_roles = 1  # Active Role
        assert count == expected_active_roles

        count, inactive_roles = crud.crud_roles.get_multi(is_active=False)
        assert count == 1
        assert inactive_roles[0].name == "Inactive Role"

    def test_delete_role(self, db_session: Session, user_context: Generator[None, None, None]) -> None:  # noqa: ARG002
        """Test deleting a role (hard delete)."""
        # Set the database session in context
        db_conn_ctx_var.set(db_session)

        # Create a test role
        role = create_test_role(db_session, name="To Delete")
        role_id = role.id

        # Delete the role (hard delete)
        deleted_role = crud.crud_roles.delete(id=role_id)

        assert deleted_role.id == role_id

        # Verify role is completely removed
        retrieved_role = crud.crud_roles.get(id=role_id)
        assert retrieved_role is None  # Should not be found after deletion
