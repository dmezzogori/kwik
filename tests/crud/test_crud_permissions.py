"""Tests for permission CRUD operations."""

from __future__ import annotations

import pytest

from kwik.crud import crud_permissions
from kwik.exceptions import EntityNotFoundError
from kwik.schemas import PermissionDefinition, PermissionUpdate
from tests.utils import create_test_permission


class TestPermissionCRUD:
    """Test cases for permission CRUD operations."""

    def test_create_permission(self) -> None:
        """Test creating a new permission."""
        permission_data = PermissionDefinition(name="test_permission")

        created_permission = crud_permissions.create(obj_in=permission_data)

        assert created_permission.name == "test_permission"
        assert created_permission.id is not None

    def test_create_permission_duplicate_name_allowed(self) -> None:
        """Test that creating permissions with duplicate names is allowed."""
        # Create first permission
        permission_data = PermissionDefinition(name="duplicate_permission")
        perm1 = crud_permissions.create(obj_in=permission_data)

        # Create second permission with same name (should be allowed)
        permission_data2 = PermissionDefinition(name="duplicate_permission")
        perm2 = crud_permissions.create(obj_in=permission_data2)

        # Both permissions should exist with different IDs
        assert perm1.id != perm2.id
        assert perm1.name == perm2.name == "duplicate_permission"

    def test_get_permission_by_id(self) -> None:
        """Test getting a permission by ID."""
        # Create a test permission
        permission = create_test_permission(name="get_test_permission")

        # Get the permission by ID
        retrieved_permission = crud_permissions.get(id=permission.id)

        assert retrieved_permission is not None
        assert retrieved_permission.id == permission.id
        assert retrieved_permission.name == "get_test_permission"

    def test_get_permission_by_nonexistent_id_returns_none(self) -> None:
        """Test getting a permission by non-existent ID returns None."""
        retrieved_permission = crud_permissions.get(id=99999)
        assert retrieved_permission is None

    def test_get_permission_by_name(self) -> None:
        """Test getting a permission by name."""
        # Create a test permission
        permission = create_test_permission(name="unique_permission")

        # Get the permission by name
        retrieved_permission = crud_permissions.get_by_name(name="unique_permission")

        assert retrieved_permission is not None
        assert retrieved_permission.id == permission.id
        assert retrieved_permission.name == "unique_permission"

    def test_get_permission_by_nonexistent_name_returns_none(self) -> None:
        """Test getting a permission by non-existent name returns None."""
        retrieved_permission = crud_permissions.get_by_name(name="nonexistent_permission")
        assert retrieved_permission is None

    def test_update_permission(self) -> None:
        """Test updating a permission."""
        # Create a test permission
        permission = create_test_permission(name="original_permission")

        # Update the permission
        update_data = PermissionUpdate(name="updated_permission")
        updated_permission = crud_permissions.update(db_obj=permission, obj_in=update_data)

        assert updated_permission.id == permission.id
        assert updated_permission.name == "updated_permission"

    def test_get_if_exist_with_existing_permission(self) -> None:
        """Test get_if_exist with an existing permission."""
        # Create a test permission
        permission = create_test_permission()

        # Get the permission using get_if_exist
        retrieved_permission = crud_permissions.get_if_exist(id=permission.id)

        assert retrieved_permission.id == permission.id

    def test_get_if_exist_with_nonexistent_permission_raises_error(self) -> None:
        """Test get_if_exist with non-existent permission raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            crud_permissions.get_if_exist(id=99999)

    def test_get_multi_permissions(self) -> None:
        """Test getting multiple permissions with pagination."""
        # Test constants
        total_permissions = 5
        page_limit = 3
        remaining_permissions = 2

        # Create multiple test permissions
        permissions = []
        for i in range(total_permissions):
            permission = create_test_permission(name=f"permission_{i}")
            permissions.append(permission)

        # Get multiple permissions
        count, retrieved_permissions = crud_permissions.get_multi(skip=0, limit=page_limit)

        assert count == total_permissions  # Total count
        assert len(retrieved_permissions) == page_limit  # Limited to 3

        # Test pagination
        count, second_page = crud_permissions.get_multi(skip=page_limit, limit=page_limit)
        assert count == total_permissions
        assert len(second_page) == remaining_permissions  # Remaining permissions
