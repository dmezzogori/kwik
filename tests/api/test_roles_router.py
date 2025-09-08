"""
Test module for roles API endpoints.

This module contains comprehensive test cases for the roles router endpoints including:
- Role management operations (list, create, get, update, delete)
- Role-permission relationship operations
- Role-user relationship operations
- Permission-based access control testing
- Validation and error handling
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from kwik.models import User
    from kwik.testing import IdentityAwareTestClient


NONEXISTENT_ROLE_ID = 99999
NONEXISTENT_USER_ID = 99999
NONEXISTENT_PERMISSION_ID = 99999
PAGINATION_DEFAULT_LIMIT = 10


class TestRolesRouter:
    """Test cases for roles router API endpoints."""

    def _create_test_role_via_api(
        self,
        identity_aware_client: IdentityAwareTestClient,
        admin_user: User,
        name: str,
        *,
        is_active: bool = True,
    ) -> dict:
        """Create a role via API for testing purposes."""
        role_data = {"name": name, "is_active": is_active}
        response = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)
        assert response.status_code == HTTPStatus.OK
        return response.json()

    def _create_test_user_via_api(  # noqa: PLR0913
        self,
        identity_aware_client: IdentityAwareTestClient,
        admin_user: User,
        email: str,
        name: str = "testuser",
        surname: str = "testsurname",
        password: str = "testpassword123",
        *,
        is_active: bool = True,
    ) -> dict:
        """Create a user via API for testing purposes."""
        user_data = {
            "name": name,
            "surname": surname,
            "email": email,
            "password": password,
            "is_active": is_active,
        }
        response = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=user_data)
        assert response.status_code == HTTPStatus.OK
        return response.json()

    def _create_test_permission_via_api(
        self,
        identity_aware_client: IdentityAwareTestClient,
        admin_user: User,
        name: str,
    ) -> dict:
        """Create a permission via API for testing purposes."""
        permission_data = {"name": name}
        response = identity_aware_client.post_as(admin_user, "/api/v1/permissions/", json=permission_data)
        assert response.status_code == HTTPStatus.OK
        return response.json()

    # Tests for GET /roles/ - List roles
    def test_list_roles_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test listing roles with admin permissions."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)

        # Admin role is created during setup, so we should have at least 1 role
        assert data["total"] > 0

        # Check role structure if any exist
        if data["data"]:
            role = data["data"][0]
            assert "id" in role
            assert "name" in role
            assert "is_active" in role

    def test_list_roles_with_pagination(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test listing roles with pagination parameters."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/?skip=0&limit=10")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) <= PAGINATION_DEFAULT_LIMIT

    def test_list_roles_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test listing roles without required permission fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/roles/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_list_roles_without_authentication(self, client: TestClient) -> None:
        """Test listing roles without authentication fails."""
        response = client.get("/api/v1/roles/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for POST /roles/ - Create role
    def test_create_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating a new role with admin permissions."""
        role_data = {"name": "test_role_create", "is_active": True}
        response = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == role_data["name"]
        assert data["is_active"] == role_data["is_active"]
        assert "id" in data

    def test_create_role_duplicate_name(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test creating role with duplicate name fails."""
        role_data = {"name": "test_role_duplicate", "is_active": True}

        # Create first role
        response1 = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)
        assert response1.status_code == HTTPStatus.OK

        # Try to create duplicate
        response2 = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)
        assert response2.status_code == HTTPStatus.CONFLICT

    def test_create_role_missing_name(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test creating role with missing required name field fails."""
        role_data = {"is_active": True}
        response = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_role_missing_is_active(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating role with missing required is_active field fails."""
        role_data = {"name": "test_role_missing_active"}
        response = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_role_empty_name(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test creating role with empty name fails."""
        role_data = {"name": "", "is_active": True}
        response = identity_aware_client.post_as(admin_user, "/api/v1/roles/", json=role_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test creating role without required permission fails."""
        role_data = {"name": "test_role_no_perm", "is_active": True}
        response = identity_aware_client.post_as(regular_user, "/api/v1/roles/", json=role_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_create_role_without_authentication(self, client: TestClient) -> None:
        """Test creating role without authentication fails."""
        role_data = {"name": "test_role_no_auth", "is_active": True}
        response = client.post("/api/v1/roles/", json=role_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /roles/{role_id} - Get role by ID
    def test_get_role_by_id_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting role by ID with admin permissions."""
        # Create test role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_get_by_id")
        role_id = created_role["id"]

        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_get_by_id"
        assert "is_active" in data

    def test_get_role_by_id_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting non-existent role by ID fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_role_by_id_invalid_id(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test getting role with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_role_by_id_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting role by ID without required permission fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/roles/1")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_role_by_id_without_authentication(self, client: TestClient) -> None:
        """Test getting role by ID without authentication fails."""
        response = client.get("/api/v1/roles/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for PUT /roles/{role_id} - Update role
    def test_update_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating role with admin permissions."""
        # Create test role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_update_before")
        role_id = created_role["id"]

        update_data = {"name": "test_role_update_after", "is_active": False}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/roles/{role_id}", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_update_after"
        assert data["is_active"] is False

    def test_update_role_partial_fields(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test updating role with only some fields."""
        # Create test role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_update_partial")
        role_id = created_role["id"]

        update_data = {"name": "test_role_updated_name"}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/roles/{role_id}", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_updated_name"
        # is_active should remain unchanged
        assert data["is_active"] == created_role["is_active"]

    def test_update_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating non-existent role by ID fails."""
        update_data = {"name": "test_role_should_fail"}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}", json=update_data)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_role_empty_data(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test updating role with empty data fails (at least one field must be provided)."""
        # Create test role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_update_empty")
        role_id = created_role["id"]

        update_data = {}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/roles/{role_id}", json=update_data)

        # Empty data is invalid since at least one field must be provided
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data  # Validation error response format

    def test_update_role_empty_name(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test updating role with empty name fails."""
        # Create test role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_update_empty_name")
        role_id = created_role["id"]

        update_data = {"name": ""}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/roles/{role_id}", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_role_invalid_id(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test updating role with invalid ID format."""
        update_data = {"name": "test_role_should_fail"}
        response = identity_aware_client.put_as(admin_user, "/api/v1/roles/invalid-id", json=update_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test updating role without required permission fails."""
        update_data = {"name": "test_role_should_fail"}
        response = identity_aware_client.put_as(regular_user, "/api/v1/roles/1", json=update_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_update_role_without_authentication(self, client: TestClient) -> None:
        """Test updating role without authentication fails."""
        update_data = {"name": "test_role_should_fail"}
        response = client.put("/api/v1/roles/1", json=update_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /roles/{role_id} - Delete role
    def test_delete_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test deleting a role with admin permissions."""
        # Create test role
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_delete")
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_delete"

        # Verify role is actually deleted by trying to get it
        get_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}")
        assert get_response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test deleting non-existent role fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_role_invalid_id(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test deleting role with invalid ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/roles/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_delete_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test deleting role without required permission fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/roles/1")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_delete_role_without_authentication(self, client: TestClient) -> None:
        """Test deleting role without authentication fails."""
        response = client.delete("/api/v1/roles/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /roles/{role_id}/permissions - Get role permissions
    def test_get_role_permissions_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting role permissions with admin permissions."""
        # Create test role and permission
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_permissions")
        role_id = created_role["id"]
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_for_role"
        )
        permission_id = created_permission["id"]

        # Assign permission to role
        assignment_data = {"permission_id": permission_id}
        assign_response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/permissions", json=assignment_data
        )
        assert assign_response.status_code == HTTPStatus.OK

        # Test getting role permissions
        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Should have the assigned permission
        assert len(data) >= 1

        # Check permission structure
        found_permission = next((p for p in data if p["id"] == permission_id), None)
        assert found_permission is not None
        assert found_permission["name"] == "test_permission_for_role"

    def test_get_role_permissions_empty_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permissions for role with no permissions."""
        # Create test role without permissions
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_empty_permissions")
        role_id = created_role["id"]

        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_role_permissions_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permissions for non-existent role fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/permissions")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_role_permissions_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting role permissions with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/invalid-id/permissions")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_role_permissions_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting role permissions without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/roles/1/permissions")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_role_permissions_without_authentication(self, client: TestClient) -> None:
        """Test getting role permissions without authentication fails."""
        response = client.get("/api/v1/roles/1/permissions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /roles/{role_id}/available-permissions - Get available permissions for role
    def test_get_role_available_permissions_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting available permissions for a role."""
        # Create test role and permission
        created_role = self._create_test_role_via_api(
            identity_aware_client, admin_user, "test_role_available_permissions"
        )
        role_id = created_role["id"]
        self._create_test_permission_via_api(identity_aware_client, admin_user, "test_available_permission_for_role")

        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/available-permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the created permission available for assignment
        if data:
            permission = data[0]
            assert "id" in permission
            assert "name" in permission

    def test_get_role_available_permissions_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting available permissions for non-existent role fails."""
        response = identity_aware_client.get_as(
            admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/available-permissions"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_role_available_permissions_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting role available permissions with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/invalid-id/available-permissions")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_role_available_permissions_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting role available permissions without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/roles/1/available-permissions")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_role_available_permissions_without_authentication(self, client: TestClient) -> None:
        """Test getting role available permissions without authentication fails."""
        response = client.get("/api/v1/roles/1/available-permissions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for POST /roles/{role_id}/permissions - Assign permission to role
    def test_assign_permission_to_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning permission to role with admin permissions."""
        # Create test role and permission
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_assign_permission")
        role_id = created_role["id"]
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_assign"
        )
        permission_id = created_permission["id"]

        assignment_data = {"permission_id": permission_id}
        response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/permissions", json=assignment_data
        )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_assign_permission"

        # Verify permission was actually assigned
        permissions_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/permissions")
        permissions_data = permissions_response.json()
        permission_ids = [p["id"] for p in permissions_data]
        assert permission_id in permission_ids

    def test_assign_permission_to_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning permission to non-existent role fails."""
        # Create permission first
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_assign_fail"
        )
        permission_id = created_permission["id"]

        assignment_data = {"permission_id": permission_id}
        response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/permissions", json=assignment_data
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_assign_permission_to_role_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning non-existent permission to role fails."""
        # Create role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_assign_fail")
        role_id = created_role["id"]

        assignment_data = {"permission_id": NONEXISTENT_PERMISSION_ID}
        response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/permissions", json=assignment_data
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_assign_permission_to_role_missing_permission_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning permission with missing permission_id fails."""
        # Create role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_assign_missing")
        role_id = created_role["id"]

        assignment_data = {}
        response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/permissions", json=assignment_data
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_assign_permission_to_role_invalid_role_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning permission with invalid role ID format."""
        assignment_data = {"permission_id": 1}
        response = identity_aware_client.post_as(
            admin_user, "/api/v1/roles/invalid-id/permissions", json=assignment_data
        )
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_assign_permission_to_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test assigning permission to role without required permissions fails."""
        assignment_data = {"permission_id": 1}
        response = identity_aware_client.post_as(regular_user, "/api/v1/roles/1/permissions", json=assignment_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_assign_permission_to_role_without_authentication(self, client: TestClient) -> None:
        """Test assigning permission to role without authentication fails."""
        assignment_data = {"permission_id": 1}
        response = client.post("/api/v1/roles/1/permissions", json=assignment_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /roles/{role_id}/permissions/{permission_id} - Remove permission from role
    def test_remove_permission_from_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing permission from role with admin permissions."""
        # Create test role and permission, then assign it
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_permission")
        role_id = created_role["id"]
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_remove"
        )
        permission_id = created_permission["id"]

        # Assign permission first
        assignment_data = {"permission_id": permission_id}
        assign_response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/permissions", json=assignment_data
        )
        assert assign_response.status_code == HTTPStatus.OK

        # Remove permission
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/permissions/{permission_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_remove_permission"

        # Verify permission was actually removed
        permissions_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/permissions")
        permissions_data = permissions_response.json()
        permission_ids = [p["id"] for p in permissions_data]
        assert permission_id not in permission_ids

    def test_remove_permission_from_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing permission from non-existent role fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/permissions/1")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remove_permission_from_role_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing non-existent permission from role fails."""
        # Create role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_fail")
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(
            admin_user, f"/api/v1/roles/{role_id}/permissions/{NONEXISTENT_PERMISSION_ID}"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remove_permission_from_role_invalid_role_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing permission with invalid role ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/roles/invalid-id/permissions/1")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_remove_permission_from_role_invalid_permission_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing permission with invalid permission ID format."""
        # Create role first
        created_role = self._create_test_role_via_api(
            identity_aware_client, admin_user, "test_role_remove_invalid_perm"
        )
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/permissions/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_remove_permission_from_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test removing permission from role without required permissions fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/roles/1/permissions/1")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_remove_permission_from_role_without_authentication(self, client: TestClient) -> None:
        """Test removing permission from role without authentication fails."""
        response = client.delete("/api/v1/roles/1/permissions/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /roles/{role_id}/permissions - Remove all permissions from role
    def test_remove_all_permissions_from_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all permissions from role with admin permissions."""
        # Create test role and permissions, then assign them
        created_role = self._create_test_role_via_api(
            identity_aware_client, admin_user, "test_role_remove_all_permissions"
        )
        role_id = created_role["id"]
        permission1 = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_remove_all_1"
        )
        permission2 = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_remove_all_2"
        )

        # Assign both permissions
        for permission in [permission1, permission2]:
            assignment_data = {"permission_id": permission["id"]}
            assign_response = identity_aware_client.post_as(
                admin_user, f"/api/v1/roles/{role_id}/permissions", json=assignment_data
            )
            assert assign_response.status_code == HTTPStatus.OK

        # Remove all permissions
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_remove_all_permissions"

        # Verify all permissions were removed
        permissions_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/permissions")
        permissions_data = permissions_response.json()
        assert len(permissions_data) == 0

    def test_remove_all_permissions_from_role_no_permissions(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all permissions from role that has no permissions."""
        # Create role without permissions
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_all_empty")
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id

    def test_remove_all_permissions_from_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all permissions from non-existent role fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/permissions")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remove_all_permissions_from_role_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all permissions with invalid role ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/roles/invalid-id/permissions")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_remove_all_permissions_from_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test removing all permissions from role without required permissions fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/roles/1/permissions")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_remove_all_permissions_from_role_without_authentication(self, client: TestClient) -> None:
        """Test removing all permissions from role without authentication fails."""
        response = client.delete("/api/v1/roles/1/permissions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /roles/{role_id}/users - Get users with role
    def test_get_users_with_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting users with role with admin permissions."""
        # Create test role and user
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_users")
        role_id = created_role["id"]
        created_user = self._create_test_user_via_api(identity_aware_client, admin_user, "testuser@role.com")
        user_id = created_user["id"]

        # Assign user to role
        assignment_data = {"user_id": user_id}
        assign_response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/users", json=assignment_data
        )
        assert assign_response.status_code == HTTPStatus.OK

        # Test getting users with role
        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/users")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Should have the assigned user
        assert len(data) >= 1

        # Check user structure
        found_user = next((u for u in data if u["id"] == user_id), None)
        assert found_user is not None
        assert found_user["email"] == "testuser@role.com"

    def test_get_users_with_role_empty_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting users for role with no users."""
        # Create test role without users
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_empty_users")
        role_id = created_role["id"]

        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/users")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_users_with_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting users for non-existent role fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/users")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_users_with_role_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting users with role with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/invalid-id/users")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_users_with_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting users with role without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/roles/1/users")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_users_with_role_without_authentication(self, client: TestClient) -> None:
        """Test getting users with role without authentication fails."""
        response = client.get("/api/v1/roles/1/users")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /roles/{role_id}/available-users - Get available users for role
    def test_get_role_available_users_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting available users for a role."""
        # Create test role and user
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_available_users")
        role_id = created_role["id"]
        self._create_test_user_via_api(identity_aware_client, admin_user, "available@role.com")

        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/available-users")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the created user available for assignment
        if data:
            user = data[0]
            assert "id" in user
            assert "email" in user
            assert "name" in user
            assert "surname" in user

    def test_get_role_available_users_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting available users for non-existent role returns empty list."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/available-users")

        # The implementation doesn't validate role existence, just returns available users
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_role_available_users_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting role available users with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/roles/invalid-id/available-users")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_role_available_users_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting role available users without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/roles/1/available-users")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_role_available_users_without_authentication(self, client: TestClient) -> None:
        """Test getting role available users without authentication fails."""
        response = client.get("/api/v1/roles/1/available-users")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for POST /roles/{role_id}/users - Assign user to role
    def test_assign_user_to_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning user to role with admin permissions."""
        # Create test role and user
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_assign_user")
        role_id = created_role["id"]
        created_user = self._create_test_user_via_api(identity_aware_client, admin_user, "assign@role.com")
        user_id = created_user["id"]

        assignment_data = {"user_id": user_id}
        response = identity_aware_client.post_as(admin_user, f"/api/v1/roles/{role_id}/users", json=assignment_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_assign_user"

        # Verify user was actually assigned
        users_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/users")
        users_data = users_response.json()
        user_ids = [u["id"] for u in users_data]
        assert user_id in user_ids

    def test_assign_user_to_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning user to non-existent role fails."""
        # Create user first
        created_user = self._create_test_user_via_api(identity_aware_client, admin_user, "assign@fail.com")
        user_id = created_user["id"]

        assignment_data = {"user_id": user_id}
        response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/users", json=assignment_data
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_assign_user_to_role_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning non-existent user to role fails."""
        # Create role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_assign_fail")
        role_id = created_role["id"]

        assignment_data = {"user_id": NONEXISTENT_USER_ID}
        response = identity_aware_client.post_as(admin_user, f"/api/v1/roles/{role_id}/users", json=assignment_data)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_assign_user_to_role_missing_user_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning user with missing user_id fails."""
        # Create role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_assign_missing")
        role_id = created_role["id"]

        assignment_data = {}
        response = identity_aware_client.post_as(admin_user, f"/api/v1/roles/{role_id}/users", json=assignment_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_assign_user_to_role_invalid_role_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test assigning user with invalid role ID format."""
        assignment_data = {"user_id": 1}
        response = identity_aware_client.post_as(admin_user, "/api/v1/roles/invalid-id/users", json=assignment_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_assign_user_to_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test assigning user to role without required permissions fails."""
        assignment_data = {"user_id": 1}
        response = identity_aware_client.post_as(regular_user, "/api/v1/roles/1/users", json=assignment_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_assign_user_to_role_without_authentication(self, client: TestClient) -> None:
        """Test assigning user to role without authentication fails."""
        assignment_data = {"user_id": 1}
        response = client.post("/api/v1/roles/1/users", json=assignment_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /roles/{role_id}/users/{user_id} - Remove user from role
    def test_remove_user_from_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing user from role with admin permissions."""
        # Create test role and user, then assign user to role
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_user")
        role_id = created_role["id"]
        created_user = self._create_test_user_via_api(identity_aware_client, admin_user, "remove@role.com")
        user_id = created_user["id"]

        # Assign user first
        assignment_data = {"user_id": user_id}
        assign_response = identity_aware_client.post_as(
            admin_user, f"/api/v1/roles/{role_id}/users", json=assignment_data
        )
        assert assign_response.status_code == HTTPStatus.OK

        # Remove user
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/users/{user_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_remove_user"

        # Verify user was actually removed
        users_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/users")
        users_data = users_response.json()
        user_ids = [u["id"] for u in users_data]
        assert user_id not in user_ids

    def test_remove_user_from_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing user from non-existent role fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/users/1")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remove_user_from_role_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing non-existent user from role fails."""
        # Create role first
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_fail")
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/users/{NONEXISTENT_USER_ID}")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remove_user_from_role_invalid_role_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing user with invalid role ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/roles/invalid-id/users/1")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_remove_user_from_role_invalid_user_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing user with invalid user ID format."""
        # Create role first
        created_role = self._create_test_role_via_api(
            identity_aware_client, admin_user, "test_role_remove_invalid_user"
        )
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/users/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_remove_user_from_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test removing user from role without required permissions fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/roles/1/users/1")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_remove_user_from_role_without_authentication(self, client: TestClient) -> None:
        """Test removing user from role without authentication fails."""
        response = client.delete("/api/v1/roles/1/users/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /roles/{role_id}/users - Remove all users from role
    def test_remove_all_users_from_role_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all users from role with admin permissions."""
        # Create test role and users, then assign them
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_all_users")
        role_id = created_role["id"]
        user1 = self._create_test_user_via_api(identity_aware_client, admin_user, "user1@removeall.com")
        user2 = self._create_test_user_via_api(identity_aware_client, admin_user, "user2@removeall.com")

        # Assign both users
        for user in [user1, user2]:
            assignment_data = {"user_id": user["id"]}
            assign_response = identity_aware_client.post_as(
                admin_user, f"/api/v1/roles/{role_id}/users", json=assignment_data
            )
            assert assign_response.status_code == HTTPStatus.OK

        # Remove all users
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/users")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id
        assert data["name"] == "test_role_remove_all_users"

        # Verify all users were removed
        users_response = identity_aware_client.get_as(admin_user, f"/api/v1/roles/{role_id}/users")
        users_data = users_response.json()
        assert len(users_data) == 0

    def test_remove_all_users_from_role_no_users(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all users from role that has no users."""
        # Create role without users
        created_role = self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_remove_all_empty")
        role_id = created_role["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{role_id}/users")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == role_id

    def test_remove_all_users_from_role_nonexistent_role(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all users from non-existent role fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/roles/{NONEXISTENT_ROLE_ID}/users")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_remove_all_users_from_role_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test removing all users with invalid role ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/roles/invalid-id/users")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_remove_all_users_from_role_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test removing all users from role without required permissions fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/roles/1/users")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_remove_all_users_from_role_without_authentication(self, client: TestClient) -> None:
        """Test removing all users from role without authentication fails."""
        response = client.delete("/api/v1/roles/1/users")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
