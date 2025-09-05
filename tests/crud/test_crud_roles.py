"""Tests for role CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kwik.core.enum import Permissions
from kwik.crud import UserCtx, crud_roles, crud_users
from kwik.exceptions import DuplicatedEntityError, EntityNotFoundError
from kwik.schemas import RoleDefinition, RoleUpdate

if TYPE_CHECKING:
    from collections.abc import Callable

    from kwik.models import Permission, Role, User


class TestRoleCRUD:
    """Test cases for role CRUD operations."""

    def test_create_role(self, admin_context: UserCtx) -> None:
        """Test creating a new role."""
        role_data = RoleDefinition(name="test_role", is_active=True)

        created_role = crud_roles.create(obj_in=role_data, context=admin_context)

        assert created_role.name == "test_role"
        assert created_role.is_active is True
        assert created_role.id is not None

    def test_get_role_by_id(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test getting a role by ID."""
        # Create a test role using the factory fixture
        role = role_factory(name="test_role")

        # Get the role by ID
        retrieved_role = crud_roles.get(entity_id=role.id, context=admin_context)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == "test_role"

    def test_get_role_by_nonexistent_id_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a role by non-existent ID returns None."""
        retrieved_role = crud_roles.get(entity_id=99999, context=admin_context)
        assert retrieved_role is None

    def test_update_role(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test updating a role."""
        # Create a test role
        role = role_factory(name="original_role")

        # Update the role
        update_data = RoleUpdate(name="updated_role")
        updated_role = crud_roles.update(entity_id=role.id, obj_in=update_data, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "updated_role"
        assert updated_role.is_active == role.is_active  # Should remain unchanged

    def test_get_if_exist_with_existing_role(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test get_if_exist with an existing role."""
        # Create a test role
        role = role_factory()

        # Get the role using get_if_exist
        retrieved_role = crud_roles.get_if_exist(entity_id=role.id, context=admin_context)

        assert retrieved_role.id == role.id

    def test_get_if_exist_with_nonexistent_role_raises_error(self, admin_context: UserCtx) -> None:
        """Test get_if_exist with non-existent role raises NotFound."""
        with pytest.raises(EntityNotFoundError):
            crud_roles.get_if_exist(entity_id=99999, context=admin_context)

    def test_get_multi_roles(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test getting multiple roles with pagination."""
        initial_roles = 1  # count for the impersonation role setup in the conftest

        # Test constants
        total_roles = 5
        page_limit = 3
        remaining_roles = 2

        # Create multiple test roles using factory fixture
        roles = []
        for i in range(total_roles):
            role = role_factory(name=f"Role {i}")
            roles.append(role)

        # Get multiple roles
        count, retrieved_roles = crud_roles.get_multi(skip=0, limit=page_limit, context=admin_context)

        assert count == total_roles + initial_roles  # Total count
        assert len(retrieved_roles) == page_limit  # Limited to 3

        # Test pagination
        count, second_page = crud_roles.get_multi(skip=page_limit, limit=page_limit, context=admin_context)
        assert count == total_roles + initial_roles
        assert len(second_page) == remaining_roles + initial_roles  # Remaining roles

    def test_get_multi_with_filters(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test getting multiple roles with filters."""
        # Create test roles with different attributes
        role_factory(name="active_role", is_active=True)
        role_factory(name="inactive_role", is_active=False)

        # Filter by is_active
        count, _ = crud_roles.get_multi(is_active=True, context=admin_context)
        expected_active_roles = 2  # Active Role + Impersonation Role
        assert count == expected_active_roles

        count, inactive_roles = crud_roles.get_multi(is_active=False, context=admin_context)
        assert count == 1
        assert inactive_roles[0].name == "inactive_role"

    def test_delete_role(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test deleting a role (hard delete)."""
        # Create a test role
        role = role_factory(name="to_delete")
        role_id = role.id

        # Delete the role (hard delete)
        deleted_role = crud_roles.delete(entity_id=role_id, context=admin_context)

        assert deleted_role is not None
        assert deleted_role.id == role_id

        # Verify role is completely removed
        retrieved_role = crud_roles.get(entity_id=role_id, context=admin_context)
        assert retrieved_role is None  # Should not be found after deletion

    def test_get_by_name_existing_role(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test getting a role by name when it exists."""
        role_name = "unique_role_name"
        role = role_factory(name=role_name)

        retrieved_role = crud_roles.get_by_name(name=role_name, context=admin_context)

        assert retrieved_role is not None
        assert retrieved_role.id == role.id
        assert retrieved_role.name == role_name

    def test_get_by_name_nonexistent_role_returns_none(self, admin_context: UserCtx) -> None:
        """Test getting a role by name when it doesn't exist returns None."""
        nonexistent_name = "Nonexistent Role"

        retrieved_role = crud_roles.get_by_name(name=nonexistent_name, context=admin_context)

        assert retrieved_role is None

    def test_get_users_with_role_having_users(
        self, role_factory: Callable[..., Role], user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test getting users associated with a role that has users."""
        role = role_factory(name="Role With Users")

        user1 = user_factory(name="User1", email="user1@test.com")
        user2 = user_factory(name="User2", email="user2@test.com")
        user3 = user_factory(name="User3", email="user3@test.com")

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

    def test_get_users_with_role_having_no_users(self, role_factory: Callable[..., Role]) -> None:
        """Test getting users associated with a role that has no users."""
        role = role_factory(name="Role Without Users")

        users_with_role = crud_roles.get_users_with(role=role)

        assert len(users_with_role) == 0
        assert users_with_role == []

    def test_get_users_without_specific_role(
        self,
        role_factory: Callable[..., Role],
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """Test getting users not associated with a specific role."""
        target_role = role_factory(name="Target Role")
        other_role = role_factory(name="Other Role")

        user_with_target_role = user_factory(name="UserWithTarget", email="with_target@test.com")
        user_with_other_role = user_factory(name="UserWithOther", email="with_other@test.com")
        user_with_no_role = user_factory(name="UserWithNoRole", email="no_role@test.com")

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
        self, role_factory: Callable[..., Role], user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test getting users not associated with a role when all users have no roles."""
        target_role = role_factory(name="Unused Role")

        user1 = user_factory(name="User1", email="user1@test.com")
        user2 = user_factory(name="User2", email="user2@test.com")

        users_without_role = crud_roles.get_users_without(role_id=target_role.id, context=admin_context)

        user_ids = {user.id for user in users_without_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        minimum_expected_users = 2
        assert len(users_without_role) >= minimum_expected_users

    def test_get_users_without_nonexistent_role_id(
        self, user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test getting users not associated with a non-existent role ID."""
        nonexistent_role_id = 99999

        user1 = user_factory(name="User1", email="user1@test.com")
        user2 = user_factory(name="User2", email="user2@test.com")

        users_without_role = crud_roles.get_users_without(role_id=nonexistent_role_id, context=admin_context)

        user_ids = {user.id for user in users_without_role}
        assert user1.id in user_ids
        assert user2.id in user_ids
        minimum_expected_users = 2
        assert len(users_without_role) >= minimum_expected_users

    def test_get_permissions_assignable_to_role_with_some_permissions(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test getting permissions assignable to role that has some permissions assigned."""
        role = role_factory(name="Role With Some Permissions")

        assigned_permission = permission_factory(name="Assigned Permission")
        unassigned_permission = permission_factory(name="Unassigned Permission")

        crud_roles.assign_permission(role=role, permission=assigned_permission, context=admin_context)

        assignable_permissions = crud_roles.get_permissions_assignable_to(role=role, context=admin_context)

        permission_ids = {permission.id for permission in assignable_permissions}
        assert unassigned_permission.id in permission_ids
        assert assigned_permission.id not in permission_ids

    def test_get_permissions_assignable_to_role_with_no_permissions(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test getting permissions assignable to role that has no permissions assigned."""
        role = role_factory(name="Role With No Permissions")

        permission1 = permission_factory(name="Available Permission 1")
        permission2 = permission_factory(name="Available Permission 2")

        assignable_permissions = crud_roles.get_permissions_assignable_to(role=role, context=admin_context)

        assignable_permission_ids = {permission.id for permission in assignable_permissions}
        assert permission1.id in assignable_permission_ids
        assert permission2.id in assignable_permission_ids

    def test_get_permissions_assignable_to_role_with_all_permissions(self, admin_context: UserCtx) -> None:
        """Test getting permissions assignable to role that has all permissions assigned."""
        admin_role = crud_roles.get_by_name(name="admin", context=admin_context)

        assert admin_role is not None

        assignable_permissions = crud_roles.get_permissions_assignable_to(role=admin_role, context=admin_context)

        assert len(assignable_permissions) == 0

    def test_get_permissions_assignable_to_no_permissions_in_database(
        self, role_factory: Callable[..., Role], admin_context: UserCtx
    ) -> None:
        """Test getting permissions assignable to role when no permissions exist in database."""
        role = role_factory(name="Role With No Available Permissions")

        assignable_permissions = crud_roles.get_permissions_assignable_to(role=role, context=admin_context)

        # forcefully exclude built-in permissions
        assignable_permissions = [p for p in assignable_permissions if p.name not in Permissions]

        assert len(assignable_permissions) == 0
        assert assignable_permissions == []

    def test_deprecate_role_with_multiple_users(
        self,
        role_factory: Callable[..., Role],
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """Test deprecating role that has multiple users assigned."""
        expected_users_count = 3
        role = role_factory(name="role_to_deprecate")

        user1 = user_factory(name="User1", email="user1@test.com")
        user2 = user_factory(name="User2", email="user2@test.com")
        user3 = user_factory(name="User3", email="user3@test.com")

        crud_roles.assign_user(role=role, user=user1, context=admin_context)
        crud_roles.assign_user(role=role, user=user2, context=admin_context)
        crud_roles.assign_user(role=role, user=user3, context=admin_context)

        admin_context.session.refresh(role)
        users_before_deprecation = crud_roles.get_users_with(role=role)
        assert len(users_before_deprecation) == expected_users_count

        deprecated_role = crud_roles.remove_all_users(role=role, context=admin_context)

        assert deprecated_role.id == role.id
        assert deprecated_role.name == "role_to_deprecate"

        admin_context.session.refresh(deprecated_role)
        users_after_deprecation = crud_roles.get_users_with(role=deprecated_role)
        assert len(users_after_deprecation) == 0

        retrieved_user1 = crud_users.get(entity_id=user1.id, context=admin_context)
        retrieved_user2 = crud_users.get(entity_id=user2.id, context=admin_context)
        retrieved_user3 = crud_users.get(entity_id=user3.id, context=admin_context)
        assert retrieved_user1 is not None
        assert retrieved_user2 is not None
        assert retrieved_user3 is not None

    def test_deprecate_role_with_no_users(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test deprecating role that has no users assigned."""
        role = role_factory(name="role_with_no_users_to_deprecate")

        users_before_deprecation = crud_roles.get_users_with(role=role)
        assert len(users_before_deprecation) == 0

        deprecated_role = crud_roles.remove_all_users(role=role, context=admin_context)

        assert deprecated_role.id == role.id
        assert deprecated_role.name == "role_with_no_users_to_deprecate"

        admin_context.session.refresh(deprecated_role)
        users_after_deprecation = crud_roles.get_users_with(role=deprecated_role)
        assert len(users_after_deprecation) == 0

    def test_deprecate_role_still_exists_after_deprecation(
        self,
        role_factory: Callable[..., Role],
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """Test that role still exists after deprecation but with no users."""
        role = role_factory(name="role_that_still_exists")
        user = user_factory(name="User", email="user@test.com")

        crud_roles.assign_user(role=role, user=user, context=admin_context)

        deprecated_role = crud_roles.remove_all_users(role=role, context=admin_context)

        retrieved_role = admin_context.session.get(type(role), role.id)
        assert retrieved_role is not None
        assert retrieved_role.id == deprecated_role.id
        assert retrieved_role.name == "role_that_still_exists"
        assert retrieved_role.is_active == role.is_active

        admin_context.session.refresh(retrieved_role)
        assert len(crud_roles.get_users_with(role=retrieved_role)) == 0

    def test_remove_permission_from_role_with_permission(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test removing existing permission from role."""
        role = role_factory(name="role_with_permission")
        permission = permission_factory(name="permission_to_remove")

        crud_roles.assign_permission(role=role, permission=permission, context=admin_context)

        admin_context.session.refresh(role)
        permissions_before_removal = crud_roles.get_permissions_assigned_to(role=role)
        permission_ids_before = {perm.id for perm in permissions_before_removal}
        assert permission.id in permission_ids_before

        updated_role = crud_roles.remove_permission(role=role, permission=permission, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "role_with_permission"

        admin_context.session.refresh(updated_role)
        permissions_after_removal = crud_roles.get_permissions_assigned_to(role=updated_role)
        permission_ids_after = {perm.id for perm in permissions_after_removal}
        assert permission.id not in permission_ids_after

    def test_remove_permission_from_role_without_permission_idempotent(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test removing permission from role that doesn't have it (idempotent operation)."""
        role = role_factory(name="role_without_permission")
        permission = permission_factory(name="unassigned_permission")

        permissions_before = crud_roles.get_permissions_assigned_to(role=role)
        permission_ids_before = {perm.id for perm in permissions_before}
        assert permission.id not in permission_ids_before

        updated_role = crud_roles.remove_permission(role=role, permission=permission, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "role_without_permission"

        admin_context.session.refresh(updated_role)
        permissions_after = crud_roles.get_permissions_assigned_to(role=updated_role)
        permission_ids_after = {perm.id for perm in permissions_after}
        assert permission.id not in permission_ids_after
        assert len(permissions_after) == len(permissions_before)

    def test_remove_permission_permission_still_exists_after_removal(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test that permission still exists after removal from role."""
        role = role_factory(name="Role To Remove Permission From")
        permission = permission_factory(name="permission_that_still_exists")

        crud_roles.assign_permission(role=role, permission=permission, context=admin_context)

        crud_roles.remove_permission(role=role, permission=permission, context=admin_context)

        retrieved_permission = admin_context.session.get(type(permission), permission.id)
        assert retrieved_permission is not None
        assert retrieved_permission.id == permission.id
        assert retrieved_permission.name == "permission_that_still_exists"

    def test_remove_permission_role_with_multiple_permissions(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test removing one permission from role that has multiple permissions."""
        expected_remaining_permissions = 2
        role = role_factory(name="Role With Multiple Permissions")

        permission_to_remove = permission_factory(name="Permission To Remove")
        permission_to_keep1 = permission_factory(name="Permission To Keep 1")
        permission_to_keep2 = permission_factory(name="Permission To Keep 2")

        crud_roles.assign_permission(role=role, permission=permission_to_remove, context=admin_context)
        crud_roles.assign_permission(role=role, permission=permission_to_keep1, context=admin_context)
        crud_roles.assign_permission(role=role, permission=permission_to_keep2, context=admin_context)

        updated_role = crud_roles.remove_permission(role=role, permission=permission_to_remove, context=admin_context)

        admin_context.session.refresh(updated_role)
        remaining_permissions = crud_roles.get_permissions_assigned_to(role=updated_role)
        assert len(remaining_permissions) == expected_remaining_permissions

        permission_ids = {perm.id for perm in remaining_permissions}
        assert permission_to_remove.id not in permission_ids
        assert permission_to_keep1.id in permission_ids
        assert permission_to_keep2.id in permission_ids

    def test_remove_user_from_role_with_user(
        self, role_factory: Callable[..., Role], user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test removing existing user from role."""
        role = role_factory(name="role_with_user")
        user = user_factory(name="User To Remove", email="remove@test.com")

        crud_roles.assign_user(role=role, user=user, context=admin_context)

        admin_context.session.refresh(role)
        users_before_removal = crud_roles.get_users_with(role=role)
        user_ids_before = {u.id for u in users_before_removal}
        assert user.id in user_ids_before

        updated_role = crud_roles.remove_user(role=role, user=user, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "role_with_user"

        admin_context.session.refresh(updated_role)
        users_after_removal = crud_roles.get_users_with(role=updated_role)
        user_ids_after = {u.id for u in users_after_removal}
        assert user.id not in user_ids_after

    def test_remove_user_from_role_without_user_idempotent(
        self, role_factory: Callable[..., Role], user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test removing user from role that doesn't have it (idempotent operation)."""
        role = role_factory(name="role_without_user")
        user = user_factory(name="Unassigned User", email="unassigned@test.com")

        users_before = crud_roles.get_users_with(role=role)
        user_ids_before = {u.id for u in users_before}
        assert user.id not in user_ids_before

        updated_role = crud_roles.remove_user(role=role, user=user, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "role_without_user"

        admin_context.session.refresh(updated_role)
        users_after = crud_roles.get_users_with(role=updated_role)
        user_ids_after = {u.id for u in users_after}
        assert user.id not in user_ids_after
        assert len(users_after) == len(users_before)

    def test_remove_user_user_still_exists_after_removal(
        self, role_factory: Callable[..., Role], user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test that user still exists after removal from role."""
        role = role_factory(name="role_to_remove_user_from")
        user = user_factory(name="User That Still Exists", email="still_exists@test.com")

        crud_roles.assign_user(role=role, user=user, context=admin_context)

        crud_roles.remove_user(role=role, user=user, context=admin_context)

        retrieved_user = admin_context.session.get(type(user), user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.name == "User That Still Exists"

    def test_remove_user_role_with_multiple_users(
        self, role_factory: Callable[..., Role], user_factory: Callable[..., User], admin_context: UserCtx
    ) -> None:
        """Test removing one user from role that has multiple users."""
        expected_remaining_users = 2
        role = role_factory(name="Role With Multiple Users")

        user_to_remove = user_factory(name="User To Remove", email="remove@test.com")
        user_to_keep1 = user_factory(name="User To Keep 1", email="keep1@test.com")
        user_to_keep2 = user_factory(name="User To Keep 2", email="keep2@test.com")

        crud_roles.assign_user(role=role, user=user_to_remove, context=admin_context)
        crud_roles.assign_user(role=role, user=user_to_keep1, context=admin_context)
        crud_roles.assign_user(role=role, user=user_to_keep2, context=admin_context)

        updated_role = crud_roles.remove_user(role=role, user=user_to_remove, context=admin_context)

        admin_context.session.refresh(updated_role)
        remaining_users = crud_roles.get_users_with(role=updated_role)
        assert len(remaining_users) == expected_remaining_users

        user_ids = {u.id for u in remaining_users}
        assert user_to_remove.id not in user_ids
        assert user_to_keep1.id in user_ids
        assert user_to_keep2.id in user_ids

    def test_remove_all_permissions_from_role_with_permissions(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test removing all permissions from role that has permissions."""
        initial_permissions_count = 3
        role = role_factory(name="role_with_permissions")

        permission1 = permission_factory(name="Permission 1")
        permission2 = permission_factory(name="Permission 2")
        permission3 = permission_factory(name="Permission 3")

        crud_roles.assign_permission(role=role, permission=permission1, context=admin_context)
        crud_roles.assign_permission(role=role, permission=permission2, context=admin_context)
        crud_roles.assign_permission(role=role, permission=permission3, context=admin_context)

        admin_context.session.refresh(role)
        permissions_before_removal = crud_roles.get_permissions_assigned_to(role=role)
        assert len(permissions_before_removal) == initial_permissions_count

        updated_role = crud_roles.remove_all_permissions(role=role, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "role_with_permissions"

        admin_context.session.refresh(updated_role)
        permissions_after_removal = crud_roles.get_permissions_assigned_to(role=updated_role)
        assert len(permissions_after_removal) == 0
        assert permissions_after_removal == []

    def test_remove_all_permissions_from_role_with_no_permissions(
        self, role_factory: Callable[..., Role], admin_context: UserCtx
    ) -> None:
        """Test removing all permissions from role that has no permissions (idempotent operation)."""
        role = role_factory(name="role_without_permissions")

        permissions_before = crud_roles.get_permissions_assigned_to(role=role)
        assert len(permissions_before) == 0

        updated_role = crud_roles.remove_all_permissions(role=role, context=admin_context)

        assert updated_role.id == role.id
        assert updated_role.name == "role_without_permissions"

        admin_context.session.refresh(updated_role)
        permissions_after = crud_roles.get_permissions_assigned_to(role=updated_role)
        assert len(permissions_after) == 0
        assert permissions_after == []

    def test_remove_all_permissions_permissions_still_exist_after_removal(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test that permissions still exist after removal from role."""
        role = role_factory(name="Role To Remove All Permissions From")

        permission1 = permission_factory(name="permission_that_still_exists_1")
        permission2 = permission_factory(name="permission_that_still_exists_2")

        crud_roles.assign_permission(role=role, permission=permission1, context=admin_context)
        crud_roles.assign_permission(role=role, permission=permission2, context=admin_context)

        crud_roles.remove_all_permissions(role=role, context=admin_context)

        retrieved_permission1 = admin_context.session.get(type(permission1), permission1.id)
        retrieved_permission2 = admin_context.session.get(type(permission2), permission2.id)
        assert retrieved_permission1 is not None
        assert retrieved_permission2 is not None
        assert retrieved_permission1.id == permission1.id
        assert retrieved_permission2.id == permission2.id
        assert retrieved_permission1.name == "permission_that_still_exists_1"
        assert retrieved_permission2.name == "permission_that_still_exists_2"

    def test_create_if_not_exist_creates_new_role(self, admin_context: UserCtx) -> None:
        """Test create_if_not_exist creates new role when not found."""
        role_data = RoleDefinition(name="new_role", is_active=True)

        filters = {"name": "new_role"}
        created_role = crud_roles.create_if_not_exist(filters=filters, obj_in=role_data, context=admin_context)

        assert created_role.name == "new_role"
        assert created_role.is_active is True
        assert created_role.id is not None

    def test_create_if_not_exist_returns_existing_role(
        self, role_factory: Callable[..., Role], admin_context: UserCtx
    ) -> None:
        """Test create_if_not_exist returns existing role when found."""
        existing_role = role_factory(name="existing_role", is_active=True)

        role_data = RoleDefinition(name="Different Role", is_active=False)
        filters = {"name": "existing_role"}

        returned_role = crud_roles.create_if_not_exist(filters=filters, obj_in=role_data, context=admin_context)

        assert returned_role.id == existing_role.id
        assert returned_role.name == "existing_role"
        assert returned_role.is_active is True

    def test_create_if_not_exist_with_raise_on_error_creates_new(self, admin_context: UserCtx) -> None:
        """Test create_if_not_exist with raise_on_error=True creates new role when not found."""
        role_data = RoleDefinition(name="unique_new_role", is_active=True)

        filters = {"name": "unique_new_role"}
        created_role = crud_roles.create_if_not_exist(
            filters=filters, obj_in=role_data, context=admin_context, raise_on_error=True
        )

        assert created_role.name == "unique_new_role"
        assert created_role.is_active is True
        assert created_role.id is not None

    def test_create_if_not_exist_with_raise_on_error_raises_for_existing(
        self, role_factory: Callable[..., Role], admin_context: UserCtx
    ) -> None:
        """Test create_if_not_exist with raise_on_error=True raises error when role exists."""
        role_factory(name="already_exists")

        role_data = RoleDefinition(name="different_name", is_active=False)
        filters = {"name": "already_exists"}
        with pytest.raises(DuplicatedEntityError):
            crud_roles.create_if_not_exist(
                filters=filters, obj_in=role_data, context=admin_context, raise_on_error=True
            )

    def test_remove_all_permissions_role_with_mixed_permissions(
        self, role_factory: Callable[..., Role], permission_factory: Callable[..., Permission], admin_context: UserCtx
    ) -> None:
        """Test removing all permissions from role with multiple different permissions."""
        initial_permissions_count = 5
        role = role_factory(name="Role With Mixed Permissions")

        permissions = []
        for i in range(initial_permissions_count):
            permission = permission_factory(name=f"Mixed Permission {i}")
            permissions.append(permission)
            crud_roles.assign_permission(role=role, permission=permission, context=admin_context)

        admin_context.session.refresh(role)
        permissions_before_removal = crud_roles.get_permissions_assigned_to(role=role)
        assert len(permissions_before_removal) == initial_permissions_count

        permission_ids_before = {perm.id for perm in permissions_before_removal}
        for permission in permissions:
            assert permission.id in permission_ids_before

        updated_role = crud_roles.remove_all_permissions(role=role, context=admin_context)

        admin_context.session.refresh(updated_role)
        permissions_after_removal = crud_roles.get_permissions_assigned_to(role=updated_role)
        assert len(permissions_after_removal) == 0

        for permission in permissions:
            retrieved_permission = admin_context.session.get(type(permission), permission.id)
            assert retrieved_permission is not None

    def test_get_multi_with_sort_ascending(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test get_multi with ascending sort on name field."""
        role_factory(name="alpha_role")
        role_factory(name="beta_role")
        role_factory(name="gamma_role")

        sort_params = [("name", "asc")]
        count, sorted_roles = crud_roles.get_multi(sort=sort_params, context=admin_context)

        role_names = [role.name for role in sorted_roles]

        alpha_idx = role_names.index("alpha_role")
        beta_idx = role_names.index("beta_role")
        gamma_idx = role_names.index("gamma_role")

        assert alpha_idx < beta_idx < gamma_idx

    def test_get_multi_with_sort_descending(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test get_multi with descending sort on name field."""
        role_factory(name="alpha_role_2")
        role_factory(name="beta_role_2")
        role_factory(name="gamma_role_2")

        sort_params = [("name", "desc")]
        count, sorted_roles = crud_roles.get_multi(sort=sort_params, context=admin_context)

        role_names = [role.name for role in sorted_roles]

        alpha_idx = role_names.index("alpha_role_2")
        beta_idx = role_names.index("beta_role_2")
        gamma_idx = role_names.index("gamma_role_2")

        assert gamma_idx < beta_idx < alpha_idx

    def test_get_multi_with_multi_field_sort(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test get_multi with multi-field sorting (name desc, then id asc)."""
        role_factory(name="same_name")
        role_factory(name="same_name")
        role_factory(name="different_name")

        sort_params = [("name", "desc"), ("id", "asc")]
        count, sorted_roles = crud_roles.get_multi(sort=sort_params, context=admin_context)

        test_roles = [r for r in sorted_roles if r.name in ["same_name", "different_name"]]

        min_expected_roles = 3
        same_name_count = 2
        assert len(test_roles) >= min_expected_roles
        assert test_roles[0].name == "same_name"

        same_name_roles = [r for r in test_roles if r.name == "same_name"]
        assert len(same_name_roles) == same_name_count
        assert same_name_roles[0].id < same_name_roles[1].id

    def test_get_multi_with_sort_and_pagination(
        self, role_factory: Callable[..., Role], admin_context: UserCtx
    ) -> None:
        """Test get_multi with sorting combined with pagination."""
        role_names = ["alpha_paginated", "beta_paginated", "gamma_paginated", "delta_paginated"]
        created_roles = []
        for name in role_names:
            role = role_factory(name=name)
            created_roles.append(role)

        sort_params = [("name", "asc")]
        page_size = 2

        _, first_page = crud_roles.get_multi(skip=1, limit=page_size, sort=sort_params, context=admin_context)
        _, second_page = crud_roles.get_multi(
            skip=page_size + 1, limit=page_size, sort=sort_params, context=admin_context
        )

        first_page_names = [role.name for role in first_page if role.name in role_names]
        second_page_names = [role.name for role in second_page if role.name in role_names]

        all_sorted_names = first_page_names + second_page_names
        expected_order = ["alpha_paginated", "beta_paginated", "gamma_paginated", "delta_paginated"]

        for expected_name in expected_order:
            assert expected_name in all_sorted_names

        alpha_idx = all_sorted_names.index("alpha_paginated")
        beta_idx = all_sorted_names.index("beta_paginated")
        assert alpha_idx < beta_idx

    def test_get_multi_with_sort_and_filters(self, role_factory: Callable[..., Role], admin_context: UserCtx) -> None:
        """Test get_multi with sorting combined with filters."""
        role_factory(name="active_z", is_active=True)
        role_factory(name="active_a", is_active=True)
        role_factory(name="inactive_b", is_active=False)

        sort_params = [("name", "desc")]
        count, filtered_sorted_roles = crud_roles.get_multi(sort=sort_params, is_active=True, context=admin_context)

        active_test_roles = [r for r in filtered_sorted_roles if r.name.startswith("active")]

        expected_active_count = 2
        assert len(active_test_roles) == expected_active_count

        active_names = [r.name for r in active_test_roles]
        assert "active_z" in active_names
        assert "active_a" in active_names

        active_z_idx = active_names.index("active_z")
        active_a_idx = active_names.index("active_a")
        assert active_z_idx < active_a_idx
