"""
Test module for permissions API endpoints.

This module contains comprehensive test cases for the permissions router endpoints including:
- Permission management operations (list, create, get, update, delete)
- Role-permission relationship operations
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

# Constants for magic values to satisfy ruff linting
NONEXISTENT_PERMISSION_ID = 99999
PAGINATION_DEFAULT_LIMIT = 10


class TestPermissionsRouter:
    """Test cases for permissions router API endpoints."""

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

    # Tests for GET /permissions/ - List permissions
    def test_list_permissions_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test listing permissions with admin permissions."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/permissions/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)

        # Admin permissions are created during setup, so we should have permissions
        assert data["total"] > 0

        # Check permission structure if any exist
        if data["data"]:
            permission = data["data"][0]
            assert "id" in permission
            assert "name" in permission

    def test_list_permissions_with_pagination(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test listing permissions with pagination parameters."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/permissions/?skip=0&limit=10")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) <= PAGINATION_DEFAULT_LIMIT

    def test_list_permissions_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test listing permissions without required permission fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/permissions/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_list_permissions_without_authentication(self, client: TestClient) -> None:
        """Test listing permissions without authentication fails."""
        response = client.get("/api/v1/permissions/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for POST /permissions/ - Create permission
    def test_create_permission_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating a new permission with admin permissions."""
        permission_data = {"name": "test_permission_create"}
        response = identity_aware_client.post_as(admin_user, "/api/v1/permissions/", json=permission_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == permission_data["name"]
        assert "id" in data

    def test_create_permission_duplicate_name(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating permission with duplicate name fails."""
        permission_data = {"name": "test_permission_duplicate"}

        # Create first permission
        response1 = identity_aware_client.post_as(admin_user, "/api/v1/permissions/", json=permission_data)
        assert response1.status_code == HTTPStatus.OK

        # Try to create duplicate
        response2 = identity_aware_client.post_as(admin_user, "/api/v1/permissions/", json=permission_data)
        assert response2.status_code == HTTPStatus.CONFLICT

    def test_create_permission_missing_name(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating permission with missing required name field fails."""
        permission_data = {}
        response = identity_aware_client.post_as(admin_user, "/api/v1/permissions/", json=permission_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_permission_empty_name(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating permission with empty name fails."""
        permission_data = {"name": ""}
        response = identity_aware_client.post_as(admin_user, "/api/v1/permissions/", json=permission_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_permission_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test creating permission without required permission fails."""
        permission_data = {"name": "test_permission_no_perm"}
        response = identity_aware_client.post_as(regular_user, "/api/v1/permissions/", json=permission_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_create_permission_without_authentication(self, client: TestClient) -> None:
        """Test creating permission without authentication fails."""
        permission_data = {"name": "test_permission_no_auth"}
        response = client.post("/api/v1/permissions/", json=permission_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /permissions/{permission_id} - Get permission by ID
    def test_get_permission_by_id_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permission by ID with admin permissions."""
        # Create test permission first
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_get_by_id"
        )
        permission_id = created_permission["id"]

        response = identity_aware_client.get_as(admin_user, f"/api/v1/permissions/{permission_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == permission_id
        assert data["name"] == "test_permission_get_by_id"

    def test_get_permission_by_id_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting non-existent permission by ID fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/permissions/{NONEXISTENT_PERMISSION_ID}")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_permission_by_id_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permission with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/permissions/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_permission_by_id_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting permission by ID without required permission fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/permissions/1")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_permission_by_id_without_authentication(self, client: TestClient) -> None:
        """Test getting permission by ID without authentication fails."""
        response = client.get("/api/v1/permissions/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for PUT /permissions/{permission_id} - Update permission
    def test_update_permission_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating permission with admin permissions."""
        # Create test permission first
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_update_before"
        )
        permission_id = created_permission["id"]

        update_data = {"name": "test_permission_update_after"}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/permissions/{permission_id}", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == permission_id
        assert data["name"] == "test_permission_update_after"

    def test_update_permission_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating non-existent permission by ID fails."""
        update_data = {"name": "test_permission_should_fail"}
        response = identity_aware_client.put_as(
            admin_user, f"/api/v1/permissions/{NONEXISTENT_PERMISSION_ID}", json=update_data
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_permission_empty_data(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating permission with empty data fails."""
        # Create test permission first
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_update_empty"
        )
        permission_id = created_permission["id"]

        update_data = {}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/permissions/{permission_id}", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_permission_empty_name(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating permission with empty name fails."""
        # Create test permission first
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_update_empty_name"
        )
        permission_id = created_permission["id"]

        update_data = {"name": ""}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/permissions/{permission_id}", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_permission_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating permission with invalid ID format."""
        update_data = {"name": "test_permission_should_fail"}
        response = identity_aware_client.put_as(admin_user, "/api/v1/permissions/invalid-id", json=update_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_permission_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test updating permission without required permission fails."""
        update_data = {"name": "test_permission_should_fail"}
        response = identity_aware_client.put_as(regular_user, "/api/v1/permissions/1", json=update_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_update_permission_without_authentication(self, client: TestClient) -> None:
        """Test updating permission without authentication fails."""
        update_data = {"name": "test_permission_should_fail"}
        response = client.put("/api/v1/permissions/1", json=update_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /permissions/{permission_id}/roles - Get associated roles
    def test_get_permission_roles_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting roles associated with a permission."""
        # Create test permission and role
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_roles"
        )
        permission_id = created_permission["id"]
        self._create_test_role_via_api(identity_aware_client, admin_user, "test_role_for_permission")

        # Assign permission to role via API (assuming this endpoint exists)
        # For now, test the endpoint even without associations
        response = identity_aware_client.get_as(admin_user, f"/api/v1/permissions/{permission_id}/roles")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # The list might be empty since we don't have association endpoint, but structure should be correct

    def test_get_permission_roles_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting roles for non-existent permission fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/permissions/{NONEXISTENT_PERMISSION_ID}/roles")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_permission_roles_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permission roles with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/permissions/invalid-id/roles")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_permission_roles_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting permission roles without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/permissions/1/roles")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_permission_roles_without_authentication(self, client: TestClient) -> None:
        """Test getting permission roles without authentication fails."""
        response = client.get("/api/v1/permissions/1/roles")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /permissions/{permission_id}/available-roles - Get available roles
    def test_get_permission_available_roles_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting available roles for a permission."""
        # Create test permission and role
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_available_roles"
        )
        permission_id = created_permission["id"]
        self._create_test_role_via_api(identity_aware_client, admin_user, "test_available_role_for_permission")

        response = identity_aware_client.get_as(admin_user, f"/api/v1/permissions/{permission_id}/available-roles")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Should have at least the created role available for assignment
        if data:
            role = data[0]
            assert "id" in role
            assert "name" in role
            assert "is_active" in role

    def test_get_permission_available_roles_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting available roles for non-existent permission fails."""
        response = identity_aware_client.get_as(
            admin_user, f"/api/v1/permissions/{NONEXISTENT_PERMISSION_ID}/available-roles"
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_permission_available_roles_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permission available roles with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/permissions/invalid-id/available-roles")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_permission_available_roles_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting permission available roles without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/permissions/1/available-roles")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_permission_available_roles_without_authentication(self, client: TestClient) -> None:
        """Test getting permission available roles without authentication fails."""
        response = client.get("/api/v1/permissions/1/available-roles")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /permissions/{permission_id}/roles - Purge all role associations
    def test_purge_permission_roles_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test purging all role associations from a permission."""
        # Create test permission
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_purge_roles"
        )
        permission_id = created_permission["id"]

        # Purge roles (even if no associations exist, should work)
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/permissions/{permission_id}/roles")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == permission_id
        assert data["name"] == "test_permission_purge_roles"
        # Permission should still exist after purging role associations

    def test_purge_permission_roles_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test purging roles for non-existent permission fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/permissions/{NONEXISTENT_PERMISSION_ID}/roles")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_purge_permission_roles_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test purging permission roles with invalid ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/permissions/invalid-id/roles")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_purge_permission_roles_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test purging permission roles without required permission fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/permissions/1/roles")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_purge_permission_roles_without_authentication(self, client: TestClient) -> None:
        """Test purging permission roles without authentication fails."""
        response = client.delete("/api/v1/permissions/1/roles")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for DELETE /permissions/{permission_id} - Delete permission
    def test_delete_permission_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test deleting a permission with admin permissions."""
        # Create test permission
        created_permission = self._create_test_permission_via_api(
            identity_aware_client, admin_user, "test_permission_delete"
        )
        permission_id = created_permission["id"]

        response = identity_aware_client.delete_as(admin_user, f"/api/v1/permissions/{permission_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == permission_id
        assert data["name"] == "test_permission_delete"

        # Verify permission is actually deleted by trying to get it
        get_response = identity_aware_client.get_as(admin_user, f"/api/v1/permissions/{permission_id}")
        assert get_response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_permission_nonexistent_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test deleting non-existent permission fails."""
        response = identity_aware_client.delete_as(admin_user, f"/api/v1/permissions/{NONEXISTENT_PERMISSION_ID}")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_permission_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test deleting permission with invalid ID format."""
        response = identity_aware_client.delete_as(admin_user, "/api/v1/permissions/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_delete_permission_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test deleting permission without required permission fails."""
        response = identity_aware_client.delete_as(regular_user, "/api/v1/permissions/1")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_delete_permission_without_authentication(self, client: TestClient) -> None:
        """Test deleting permission without authentication fails."""
        response = client.delete("/api/v1/permissions/1")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
