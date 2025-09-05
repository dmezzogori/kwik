"""Tests for permission CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.crud import UserCtx, crud_permissions, crud_roles
from kwik.exceptions import DuplicatedEntityError, EntityNotFoundError
from kwik.schemas import PermissionDefinition, PermissionUpdate

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.models import Permission, Role


class TestPermissionCRUD:
    """Test cases for permission CRUD operations."""

    def test_create_permission(self, admin_context: UserCtx) -> None:
        """Test creating a new permission."""
        permission_data = PermissionDefinition(name="test_permission")

        created_permission = crud_permissions.create(obj_in=permission_data, context=admin_context)

        assert created_permission.name == "test_permission"
        assert created_permission.id is not None

    def test_create_permission_duplicate_name_allowed(self, admin_context: UserCtx) -> None:
        """Test that creating permissions with duplicate names is allowed."""
        # Create first permission
        permission_data = PermissionDefinition(name="duplicate_permission")
        perm1 = crud_permissions.create(obj_in=permission_data, context=admin_context)

        # Create second permission with same name (should be allowed)
        permission_data2 = PermissionDefinition(name="duplicate_permission")
        perm2 = crud_permissions.create(obj_in=permission_data2, context=admin_context)

        # Both permissions should exist with different IDs
        assert perm1.id != perm2.id
        assert perm1.name == perm2.name == "duplicate_permission"

    def test_get_permission_by_id(self, permission_factory: Callable[..., Permission], admin_context: UserCtx) -> None:
        """Test getting a permission by ID."""
        # Create a test permission
        permission = permission_factory(name="get_test_permission")

        # Get the permission by ID
        retrieved_permission = crud_permissions.get(entity_id=permission.id, context=admin_context)

        assert retrieved_permission is not None
        assert retrieved_permission.id == permission.id
        assert retrieved_permission.name == "get_test_permission"

    def test_get_permission_by_nonexistent_id_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a permission by non-existent ID returns None."""
        retrieved_permission = crud_permissions.get(entity_id=99999, context=admin_context)
        assert retrieved_permission is None

    def test_get_permission_by_name(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test getting a permission by name."""
        # Create a test permission
        permission = permission_factory(name="unique_permission")

        # Get the permission by name
        retrieved_permission = crud_permissions.get_by_name(name="unique_permission", context=admin_context)

        assert retrieved_permission is not None
        assert retrieved_permission.id == permission.id
        assert retrieved_permission.name == "unique_permission"

    def test_get_permission_by_nonexistent_name_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a permission by non-existent name returns None."""
        retrieved_permission = crud_permissions.get_by_name(name="nonexistent_permission", context=admin_context)
        assert retrieved_permission is None

    def test_update_permission(self, permission_factory: Callable[..., Permission], admin_context: UserCtx) -> None:
        """Test updating a permission."""
        # Create a test permission
        permission = permission_factory(name="original_permission")

        # Update the permission
        update_data = PermissionUpdate(name="updated_permission")
        updated_permission = crud_permissions.update(entity_id=permission.id, obj_in=update_data, context=admin_context)

        assert updated_permission.id == permission.id
        assert updated_permission.name == "updated_permission"

    def test_get_if_exist_with_existing_permission(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test get_if_exist with an existing permission."""
        # Create a test permission
        permission = permission_factory()

        # Get the permission using get_if_exist
        retrieved_permission = crud_permissions.get_if_exist(entity_id=permission.id, context=admin_context)

        assert retrieved_permission.id == permission.id

    def test_get_if_exist_with_nonexistent_permission_raises_error(self, admin_context: UserCtx) -> None:
        """Test get_if_exist with non-existent permission raises EntityNotFoundError."""
        with pytest.raises(EntityNotFoundError):
            crud_permissions.get_if_exist(entity_id=99999, context=admin_context)

    def test_get_multi_permissions(self, admin_context: UserCtx) -> None:
        """Test getting multiple permissions with pagination."""
        total_permissions = 14  # All permissions from Permissions enum are associated with admin_user
        page_limit = 5

        # Test first page
        count, first_page = crud_permissions.get_multi(skip=0, limit=page_limit, context=admin_context)
        assert count == total_permissions
        assert len(first_page) == page_limit

        # Test second page
        count, second_page = crud_permissions.get_multi(skip=page_limit, limit=page_limit, context=admin_context)
        assert count == total_permissions
        assert len(second_page) == page_limit

        # Test final page
        final_skip = 10
        remaining_permissions = total_permissions - final_skip
        count, final_page = crud_permissions.get_multi(skip=final_skip, limit=page_limit, context=admin_context)
        assert count == total_permissions
        assert len(final_page) == remaining_permissions

    def test_get_roles_assigned_to(
        self,
        permission_factory: Callable[..., Permission],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """Test getting roles assigned to a specific permission."""
        # Test constants
        expected_assigned_count = 2

        # Create test permission
        permission = permission_factory(name="test_permission")

        # Create test roles
        role1 = role_factory(name="assigned_role_1")
        role2 = role_factory(name="assigned_role_2")
        role3 = role_factory(name="unassigned_role")

        # Assign roles to permission
        crud_roles.assign_permission(role=role1, permission=permission, context=admin_context)
        crud_roles.assign_permission(role=role2, permission=permission, context=admin_context)
        # role3 is intentionally not assigned

        # Get roles assigned to the permission
        assigned_roles = crud_permissions.get_roles_assigned_to(permission=permission)

        # Assert that only assigned roles are returned
        assert len(assigned_roles) == expected_assigned_count
        assigned_role_ids = {role.id for role in assigned_roles}
        assert role1.id in assigned_role_ids
        assert role2.id in assigned_role_ids
        assert role3.id not in assigned_role_ids

        # Verify role names for clarity
        assigned_role_names = {role.name for role in assigned_roles}
        assert "assigned_role_1" in assigned_role_names
        assert "assigned_role_2" in assigned_role_names
        assert "unassigned_role" not in assigned_role_names

    def test_get_roles_assignable_to(
        self, permission_factory: Callable[..., Permission], role_factory: Callable[..., Role], admin_context: UserCtx
    ) -> None:
        """Test getting roles assignable to a specific permission."""
        # Test constants
        expected_assignable_count = 2  # counts also the impersonator role setup in conftests

        # Create test permission
        permission = permission_factory(name="test_permission")

        # Create test roles
        role1 = role_factory(name="assigned_role_1")
        role2 = role_factory(name="assigned_role_2")
        role3 = role_factory(name="assignable_role")

        # Assign some roles to permission
        crud_roles.assign_permission(role=role1, permission=permission, context=admin_context)
        crud_roles.assign_permission(role=role2, permission=permission, context=admin_context)
        # role3 is intentionally not assigned

        # Get roles assignable to the permission
        assignable_roles = crud_permissions.get_roles_assignable_to(permission=permission, context=admin_context)

        # Assert that only unassigned roles are returned
        assert len(assignable_roles) == expected_assignable_count
        assignable_role_ids = {role.id for role in assignable_roles}
        assert role3.id in assignable_role_ids
        assert role1.id not in assignable_role_ids
        assert role2.id not in assignable_role_ids

        # Verify role names for clarity
        assignable_role_names = {role.name for role in assignable_roles}
        assert "assignable_role" in assignable_role_names
        assert "assigned_role_1" not in assignable_role_names
        assert "assigned_role_2" not in assignable_role_names

    def test_purge_all_roles(
        self,
        permission_factory: Callable[..., Permission],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """Test purging all role associations from a permission."""
        # Test constants
        initial_role_count = 3
        expected_roles_after_purge = 0

        # Create test permission
        permission = permission_factory(name="test_permission_purge")

        # Create test roles
        role1 = role_factory(name="role_to_purge_1")
        role2 = role_factory(name="role_to_purge_2")
        role3 = role_factory(name="role_to_purge_3")

        # Assign all roles to permission
        crud_roles.assign_permission(role=role1, permission=permission, context=admin_context)
        crud_roles.assign_permission(role=role2, permission=permission, context=admin_context)
        crud_roles.assign_permission(role=role3, permission=permission, context=admin_context)

        # Verify initial state - permission has roles assigned
        initial_assigned_roles = crud_permissions.get_roles_assigned_to(permission=permission)
        assert len(initial_assigned_roles) == initial_role_count

        # Purge all roles from permission
        purged_permission = crud_permissions.purge_all_roles(permission_id=permission.id, context=admin_context)

        # Assert permission is returned and still exists
        assert purged_permission.id == permission.id
        assert purged_permission.name == "test_permission_purge"

        # Assert all role associations are removed
        # Refresh the permission to get updated relationships
        admin_context.session.refresh(purged_permission)
        remaining_roles = crud_permissions.get_roles_assigned_to(permission=purged_permission)
        assert len(remaining_roles) == expected_roles_after_purge

        # Assert original roles still exist but are not associated
        retrieved_role1 = crud_roles.get(entity_id=role1.id, context=admin_context)
        retrieved_role2 = crud_roles.get(entity_id=role2.id, context=admin_context)
        retrieved_role3 = crud_roles.get(entity_id=role3.id, context=admin_context)
        assert retrieved_role1 is not None
        assert retrieved_role2 is not None
        assert retrieved_role3 is not None

        # Verify all roles are now assignable to the permission
        assignable_roles = crud_permissions.get_roles_assignable_to(permission=purged_permission, context=admin_context)
        assignable_role_ids = {role.id for role in assignable_roles}
        assert role1.id in assignable_role_ids
        assert role2.id in assignable_role_ids
        assert role3.id in assignable_role_ids

    def test_purge_all_roles_nonexistent_permission_raises_error(self, admin_context: UserCtx) -> None:
        """Test purging roles from non-existent permission raises EntityNotFoundError."""
        nonexistent_permission_id = 99999

        with pytest.raises(EntityNotFoundError):
            crud_permissions.purge_all_roles(permission_id=nonexistent_permission_id, context=admin_context)

    def test_delete_permission(
        self,
        permission_factory: Callable[..., Permission],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """Test deleting a permission with role associations."""
        # Test constants
        initial_role_count = 2

        # Create test permission
        permission = permission_factory(name="permission_to_delete")

        # Create test roles
        role1 = role_factory(name="role_with_deleted_permission_1")
        role2 = role_factory(name="role_with_deleted_permission_2")

        # Assign roles to permission
        crud_roles.assign_permission(role=role1, permission=permission, context=admin_context)
        crud_roles.assign_permission(role=role2, permission=permission, context=admin_context)

        # Verify initial state - permission exists and has roles
        initial_assigned_roles = crud_permissions.get_roles_assigned_to(permission=permission)
        assert len(initial_assigned_roles) == initial_role_count

        # Delete the permission
        deleted_permission = crud_permissions.delete(entity_id=permission.id, context=admin_context)

        # Assert deleted permission is returned with correct data
        assert deleted_permission.id == permission.id
        assert deleted_permission.name == "permission_to_delete"

        # Assert permission is completely removed from database
        retrieved_permission = crud_permissions.get(entity_id=permission.id, context=admin_context)
        assert retrieved_permission is None

        # Assert original roles still exist
        retrieved_role1 = crud_roles.get(entity_id=role1.id, context=admin_context)
        retrieved_role2 = crud_roles.get(entity_id=role2.id, context=admin_context)
        assert retrieved_role1 is not None
        assert retrieved_role2 is not None

        # Verify roles no longer have the deleted permission assigned
        role1_permissions = crud_roles.get_permissions_assigned_to(role=retrieved_role1)
        role2_permissions = crud_roles.get_permissions_assigned_to(role=retrieved_role2)
        permission_ids = {perm.id for perm in role1_permissions + role2_permissions}
        assert permission.id not in permission_ids

    def test_delete_nonexistent_permission_raises_error(self, admin_context: UserCtx) -> None:
        """Test deleting non-existent permission raises EntityNotFoundError."""
        nonexistent_permission_id = 99999

        with pytest.raises(EntityNotFoundError):
            crud_permissions.delete(entity_id=nonexistent_permission_id, context=admin_context)

    def test_create_if_not_exist_creates_new_permission(self, admin_context: UserCtx) -> None:
        """Test create_if_not_exist creates new permission when not found."""
        permission_data = PermissionDefinition(name="new_permission")

        filters = {"name": "new_permission"}
        created_permission = crud_permissions.create_if_not_exist(
            filters=filters, obj_in=permission_data, context=admin_context
        )

        assert created_permission.name == "new_permission"
        assert created_permission.id is not None

    def test_create_if_not_exist_returns_existing_permission(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test create_if_not_exist returns existing permission when found."""
        existing_permission = permission_factory(name="existing_permission")

        permission_data = PermissionDefinition(name="different_permission")
        filters = {"name": "existing_permission"}

        returned_permission = crud_permissions.create_if_not_exist(
            filters=filters, obj_in=permission_data, context=admin_context
        )

        assert returned_permission.id == existing_permission.id
        assert returned_permission.name == "existing_permission"

    def test_create_if_not_exist_with_raise_on_error_creates_new(self, admin_context: UserCtx) -> None:
        """Test create_if_not_exist with raise_on_error=True creates new permission when not found."""
        permission_data = PermissionDefinition(name="unique_new_permission")

        filters = {"name": "unique_new_permission"}
        created_permission = crud_permissions.create_if_not_exist(
            filters=filters, obj_in=permission_data, context=admin_context, raise_on_error=True
        )

        assert created_permission.name == "unique_new_permission"
        assert created_permission.id is not None

    def test_create_if_not_exist_with_raise_on_error_raises_for_existing(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test create_if_not_exist with raise_on_error=True raises error when permission exists."""
        permission_factory(name="already_exists_permission")

        permission_data = PermissionDefinition(name="different_name_permission")
        filters = {"name": "already_exists_permission"}
        with pytest.raises(DuplicatedEntityError):
            crud_permissions.create_if_not_exist(
                filters=filters, obj_in=permission_data, context=admin_context, raise_on_error=True
            )

    def test_get_multi_with_sort_ascending(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test get_multi with ascending sort on name field."""
        permission_factory(name="alpha_permission")
        permission_factory(name="beta_permission")
        permission_factory(name="gamma_permission")

        sort_params = [("name", "asc")]
        count, sorted_permissions = crud_permissions.get_multi(sort=sort_params, context=admin_context)

        permission_names = [perm.name for perm in sorted_permissions]

        alpha_idx = permission_names.index("alpha_permission")
        beta_idx = permission_names.index("beta_permission")
        gamma_idx = permission_names.index("gamma_permission")

        assert alpha_idx < beta_idx < gamma_idx

    def test_get_multi_with_sort_descending(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test get_multi with descending sort on name field."""
        permission_factory(name="alpha_permission_2")
        permission_factory(name="beta_permission_2")
        permission_factory(name="gamma_permission_2")

        sort_params = [("name", "desc")]
        count, sorted_permissions = crud_permissions.get_multi(sort=sort_params, context=admin_context)

        permission_names = [perm.name for perm in sorted_permissions]

        alpha_idx = permission_names.index("alpha_permission_2")
        beta_idx = permission_names.index("beta_permission_2")
        gamma_idx = permission_names.index("gamma_permission_2")

        assert gamma_idx < beta_idx < alpha_idx

    def test_get_multi_with_multi_field_sort(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test get_multi with multi-field sorting (name desc, then id asc)."""
        permission_factory(name="same_name_permission")
        permission_factory(name="same_name_permission")
        permission_factory(name="different_name_permission")

        sort_params = [("name", "desc"), ("id", "asc")]
        count, sorted_permissions = crud_permissions.get_multi(sort=sort_params, context=admin_context)

        test_permissions = [
            p for p in sorted_permissions if p.name in ["same_name_permission", "different_name_permission"]
        ]

        min_expected_permissions = 3
        same_name_count = 2
        assert len(test_permissions) >= min_expected_permissions
        assert test_permissions[0].name == "same_name_permission"

        same_name_permissions = [p for p in test_permissions if p.name == "same_name_permission"]
        assert len(same_name_permissions) == same_name_count
        assert same_name_permissions[0].id < same_name_permissions[1].id

    def test_get_multi_with_sort_and_pagination(
        self, permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test get_multi with sorting combined with pagination."""
        permission_names = ["alpha_paginated", "beta_paginated", "gamma_paginated", "delta_paginated"]
        created_permissions = []
        for name in permission_names:
            permission = permission_factory(name=name)
            created_permissions.append(permission)

        sort_params = [("name", "asc")]
        page_size = 2

        count, first_page = crud_permissions.get_multi(skip=0, limit=page_size, sort=sort_params, context=admin_context)
        count, second_page = crud_permissions.get_multi(
            skip=page_size, limit=page_size, sort=sort_params, context=admin_context
        )

        first_page_names = [perm.name for perm in first_page if perm.name in permission_names]
        second_page_names = [perm.name for perm in second_page if perm.name in permission_names]

        all_sorted_names = first_page_names + second_page_names
        expected_order = ["alpha_paginated", "beta_paginated", "gamma_paginated", "delta_paginated"]

        for expected_name in expected_order:
            assert expected_name in all_sorted_names

        alpha_idx = all_sorted_names.index("alpha_paginated")
        beta_idx = all_sorted_names.index("beta_paginated")
        assert alpha_idx < beta_idx
