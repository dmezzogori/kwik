"""Tests for role CRUD operations."""

from __future__ import annotations

import pytest

from kwik.crud import UserCtx, crud_roles
from kwik.exceptions import EntityNotFoundError
from kwik.schemas import RoleDefinition, RoleUpdate
from tests.utils import create_test_role


class TestRoleCRUD:
    """Test cases for role CRUD operations."""

    def test_create_role(self, admin_context: UserCtx) -> None:
        """Test creating a new role."""
        role_data = RoleDefinition(name="Test Role", is_active=True)

        created_role = crud_roles.create(obj_in=role_data, context=admin_context)

        assert created_role.name == "Test Role"
        assert created_role.is_active is True
        assert created_role.id is not None

    def test_get_role_by_id(self, admin_context: UserCtx) -> None:
        """Test getting a role by ID."""
        # Create a test role
        role = create_test_role(name="Get Test Role", context=admin_context)

        # Get the role by ID
        retrieved_role = crud_roles.get(id=role.id, context=admin_context)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == "Get Test Role"

    def test_get_role_by_nonexistent_id_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a role by non-existent ID returns None."""
        retrieved_role = crud_roles.get(id=99999, context=admin_context)
        assert retrieved_role is None

    def test_update_role(self, admin_context: UserCtx) -> None:
        """Test updating a role."""
        # Create a test role
        role = create_test_role(name="Original Role", context=admin_context)

        # Update the role
        update_data = RoleUpdate(name="Updated Role")
        updated_role = crud_roles.update(id=role.id, obj_in=update_data, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "Updated Role"
        assert updated_role.is_active == role.is_active  # Should remain unchanged

    def test_get_if_exist_with_existing_role(self, admin_context: UserCtx) -> None:
        """Test get_if_exist with an existing role."""
        # Create a test role
        role = create_test_role(context=admin_context)

        # Get the role using get_if_exist
        retrieved_role = crud_roles.get_if_exist(id=role.id, context=admin_context)

        assert retrieved_role.id == role.id

    def test_get_if_exist_with_nonexistent_role_raises_error(self, admin_context: UserCtx) -> None:
        """Test get_if_exist with non-existent role raises NotFound."""
        with pytest.raises(EntityNotFoundError):
            crud_roles.get_if_exist(id=99999, context=admin_context)

    def test_get_multi_roles(self, admin_context: UserCtx) -> None:
        """Test getting multiple roles with pagination."""
        # Test constants
        total_roles = 5
        page_limit = 3
        remaining_roles = 2

        # Create multiple test roles
        roles = []
        for i in range(total_roles):
            role = create_test_role(name=f"Role {i}", context=admin_context)
            roles.append(role)

        # Get multiple roles
        count, retrieved_roles = crud_roles.get_multi(skip=0, limit=page_limit, context=admin_context)

        assert count == total_roles  # Total count
        assert len(retrieved_roles) == page_limit  # Limited to 3

        # Test pagination
        count, second_page = crud_roles.get_multi(skip=page_limit, limit=page_limit, context=admin_context)
        assert count == total_roles
        assert len(second_page) == remaining_roles  # Remaining roles

    def test_get_multi_with_filters(self, admin_context: UserCtx) -> None:
        """Test getting multiple roles with filters."""
        # Create test roles with different attributes
        create_test_role(name="Active Role", is_active=True, context=admin_context)
        create_test_role(name="Inactive Role", is_active=False, context=admin_context)

        # Filter by is_active
        count, _ = crud_roles.get_multi(is_active=True, context=admin_context)
        expected_active_roles = 1  # Active Role
        assert count == expected_active_roles

        count, inactive_roles = crud_roles.get_multi(is_active=False, context=admin_context)
        assert count == 1
        assert inactive_roles[0].name == "Inactive Role"

    def test_delete_role(self, admin_context: UserCtx) -> None:
        """Test deleting a role (hard delete)."""
        # Create a test role
        role = create_test_role(name="To Delete", context=admin_context)
        role_id = role.id

        # Delete the role (hard delete)
        deleted_role = crud_roles.delete(id=role_id, context=admin_context)

        assert deleted_role is not None
        assert deleted_role.id == role_id

        # Verify role is completely removed
        retrieved_role = crud_roles.get(id=role_id, context=admin_context)
        assert retrieved_role is None  # Should not be found after deletion
