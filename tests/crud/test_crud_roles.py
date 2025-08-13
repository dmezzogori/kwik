"""Tests for role CRUD operations."""

from __future__ import annotations

import pytest

from kwik.crud import NoUserCtx, UserCtx, crud_roles
from kwik.exceptions import EntityNotFoundError
from kwik.schemas import RoleDefinition, RoleUpdate
from tests.utils import create_test_role, create_test_user


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
        retrieved_role = crud_roles.get(entity_id=role.id, context=admin_context)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == "Get Test Role"

    def test_get_role_by_nonexistent_id_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a role by non-existent ID returns None."""
        retrieved_role = crud_roles.get(entity_id=99999, context=admin_context)
        assert retrieved_role is None

    def test_update_role(self, admin_context: UserCtx) -> None:
        """Test updating a role."""
        # Create a test role
        role = create_test_role(name="Original Role", context=admin_context)

        # Update the role
        update_data = RoleUpdate(name="Updated Role")
        updated_role = crud_roles.update(entity_id=role.id, obj_in=update_data, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "Updated Role"
        assert updated_role.is_active == role.is_active  # Should remain unchanged

    def test_get_if_exist_with_existing_role(self, admin_context: UserCtx) -> None:
        """Test get_if_exist with an existing role."""
        # Create a test role
        role = create_test_role(context=admin_context)

        # Get the role using get_if_exist
        retrieved_role = crud_roles.get_if_exist(entity_id=role.id, context=admin_context)

        assert retrieved_role.id == role.id

    def test_get_if_exist_with_nonexistent_role_raises_error(self, admin_context: UserCtx) -> None:
        """Test get_if_exist with non-existent role raises NotFound."""
        with pytest.raises(EntityNotFoundError):
            crud_roles.get_if_exist(entity_id=99999, context=admin_context)

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
        deleted_role = crud_roles.delete(entity_id=role_id, context=admin_context)

        assert deleted_role is not None
        assert deleted_role.id == role_id

        # Verify role is completely removed
        retrieved_role = crud_roles.get(entity_id=role_id, context=admin_context)
        assert retrieved_role is None  # Should not be found after deletion

    def test_get_by_name_existing_role(self, admin_context: UserCtx) -> None:
        """Test getting a role by name when it exists."""
        role_name = "Unique Role Name"
        role = create_test_role(name=role_name, context=admin_context)

        retrieved_role = crud_roles.get_by_name(name=role_name, context=admin_context)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == role_name

    def test_get_by_name_nonexistent_role_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a role by name when it doesn't exist returns None."""
        nonexistent_name = "Nonexistent Role"

        retrieved_role = crud_roles.get_by_name(name=nonexistent_name, context=admin_context)

        assert retrieved_role is None

    def test_get_users_with_role_having_users(self, admin_context: UserCtx, no_user_context: NoUserCtx) -> None:
        """Test getting users associated with a role that has users."""
        role = create_test_role(name="Role With Users", context=admin_context)

        user1 = create_test_user(name="User1", email="user1@test.com", context=no_user_context)
        user2 = create_test_user(name="User2", email="user2@test.com", context=no_user_context)
        user3 = create_test_user(name="User3", email="user3@test.com", context=no_user_context)

        crud_roles.assign_user(role=role, user=user1, context=admin_context)
        crud_roles.assign_user(role=role, user=user2, context=admin_context)
        crud_roles.assign_user(role=role, user=user3, context=admin_context)

        admin_context.session.refresh(role)

        users_with_role = crud_roles.get_users_with(role=role)

        expected_users_count = 3
        assert len(users_with_role) == expected_users_count
        user_ids = {user.id for user in users_with_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        assert user3.id in user_ids

    def test_get_users_with_role_having_no_users(self, admin_context: UserCtx) -> None:
        """Test getting users associated with a role that has no users."""
        role = create_test_role(name="Role Without Users", context=admin_context)

        users_with_role = crud_roles.get_users_with(role=role)

        assert len(users_with_role) == 0
        assert users_with_role == []

    def test_get_users_without_specific_role(self, admin_context: UserCtx, no_user_context: NoUserCtx) -> None:
        """Test getting users not associated with a specific role."""
        target_role = create_test_role(name="Target Role", context=admin_context)
        other_role = create_test_role(name="Other Role", context=admin_context)

        user_with_target_role = create_test_user(
            name="UserWithTarget", email="with_target@test.com", context=no_user_context
        )
        user_with_other_role = create_test_user(
            name="UserWithOther", email="with_other@test.com", context=no_user_context
        )
        user_with_no_role = create_test_user(name="UserWithNoRole", email="no_role@test.com", context=no_user_context)

        crud_roles.assign_user(role=target_role, user=user_with_target_role, context=admin_context)
        crud_roles.assign_user(role=other_role, user=user_with_other_role, context=admin_context)

        users_without_target_role = crud_roles.get_users_without(role_id=target_role.id, context=admin_context)

        user_ids = {user.id for user in users_without_target_role}
        assert user_with_other_role.id in user_ids
        assert user_with_no_role.id in user_ids
        assert user_with_target_role.id not in user_ids
        minimum_expected_users = 2
        assert len(users_without_target_role) >= minimum_expected_users

    def test_get_users_without_all_users_have_no_roles(
        self, admin_context: UserCtx, no_user_context: NoUserCtx
    ) -> None:
        """Test getting users not associated with a role when all users have no roles."""
        target_role = create_test_role(name="Unused Role", context=admin_context)

        user1 = create_test_user(name="User1", email="user1@test.com", context=no_user_context)
        user2 = create_test_user(name="User2", email="user2@test.com", context=no_user_context)

        users_without_role = crud_roles.get_users_without(role_id=target_role.id, context=admin_context)

        user_ids = {user.id for user in users_without_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        minimum_expected_users = 2
        assert len(users_without_role) >= minimum_expected_users

    def test_get_users_without_nonexistent_role_id(self, admin_context: UserCtx, no_user_context: NoUserCtx) -> None:
        """Test getting users not associated with a non-existent role ID."""
        nonexistent_role_id = 99999

        user1 = create_test_user(name="User1", email="user1@test.com", context=no_user_context)
        user2 = create_test_user(name="User2", email="user2@test.com", context=no_user_context)

        users_without_role = crud_roles.get_users_without(role_id=nonexistent_role_id, context=admin_context)

        user_ids = {user.id for user in users_without_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        minimum_expected_users = 2
        assert len(users_without_role) >= minimum_expected_users
