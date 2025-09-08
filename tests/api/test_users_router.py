"""
Test module for users API endpoints.

This module contains comprehensive test cases for the users router endpoints including:
- User management operations (list, create, get, update)
- Current user operations (profile, permissions, roles, password)
- User-specific operations (permissions, roles, password by admin)
- Permission-based access control testing
- Validation and error handling
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.testclient import TestClient

    from kwik.models import User
    from kwik.settings import BaseKwikSettings
    from kwik.testing import IdentityAwareTestClient

# Constants for magic values to satisfy ruff linting
TEST_USER_COUNTER_START = 1000
MIN_PASSWORD_LENGTH = 8
PAGINATION_DEFAULT_LIMIT = 10
NONEXISTENT_USER_ID = 99999


class TestUsersRouter:
    """Test cases for users router API endpoints."""

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

    # Tests for GET /users/ - List users
    def test_list_users_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test listing users with admin permissions."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert isinstance(data["data"], list)
        assert isinstance(data["total"], int)

        expected_number_of_users = 2
        assert data["total"] == expected_number_of_users

    def test_list_users_with_pagination(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test listing users with pagination parameters."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/?skip=0&limit=10")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert len(data["data"]) <= PAGINATION_DEFAULT_LIMIT

    def test_list_users_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test listing users without admin permission fails."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/users/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_list_users_without_authentication(self, client: TestClient) -> None:
        """Test listing users without authentication fails."""
        response = client.get("/api/v1/users/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for POST /users/ - Create user
    def test_create_user_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating a new user with admin permissions."""
        user_data = {
            "name": "newuser",
            "surname": "newsurname",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "is_active": True,
        }
        response = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=user_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == user_data["name"]
        assert data["surname"] == user_data["surname"]
        assert data["email"] == user_data["email"]
        assert data["is_active"] == user_data["is_active"]
        assert "id" in data

    def test_create_user_duplicate_email(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating user with duplicate email fails."""
        user_data = {
            "name": "testuser",
            "surname": "testsurname",
            "email": "duplicate@example.com",
            "password": "password123",
            "is_active": True,
        }

        # Create first user
        response1 = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=user_data)
        assert response1.status_code == HTTPStatus.OK

        # Try to create duplicate
        response2 = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=user_data)
        assert response2.status_code == HTTPStatus.CONFLICT

    def test_create_user_invalid_email(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test creating user with invalid email format fails."""
        user_data = {
            "name": "testuser",
            "surname": "testsurname",
            "email": "invalid-email-format",
            "password": "password123",
            "is_active": True,
        }
        response = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=user_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_user_missing_required_fields(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test creating user with missing required fields fails."""
        user_data = {
            "name": "testuser",
            # Missing required fields: surname, email, password
        }
        response = identity_aware_client.post_as(admin_user, "/api/v1/users/", json=user_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_create_user_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test creating user without admin permission fails."""
        user_data = {
            "name": "testuser",
            "surname": "testsurname",
            "email": "test@example.com",
            "password": "password123",
            "is_active": True,
        }
        response = identity_aware_client.post_as(regular_user, "/api/v1/users/", json=user_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_create_user_without_authentication(self, client: TestClient) -> None:
        """Test creating user without authentication fails."""
        user_data = {
            "name": "testuser",
            "surname": "testsurname",
            "email": "test@example.com",
            "password": "password123",
            "is_active": True,
        }
        response = client.post("/api/v1/users/", json=user_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /users/me - Get current user
    def test_get_current_user_as_admin(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test getting current user profile as admin."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/me")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == admin_user.id
        assert data["name"] == admin_user.name
        assert data["surname"] == admin_user.surname
        assert data["email"] == admin_user.email
        assert "is_active" in data

    def test_get_current_user_as_regular_user(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting current user profile as regular user."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/users/me")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["name"] == regular_user.name
        assert data["surname"] == regular_user.surname
        assert data["email"] == regular_user.email

    def test_get_current_user_without_authentication(self, client: TestClient) -> None:
        """Test getting current user without authentication fails."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for PUT /users/me - Update current user
    def test_update_current_user_all_fields(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating current user profile with all fields."""
        update_data = {
            "name": "UpdatedName",
            "surname": "UpdatedSurname",
            "email": "updated@example.com",
            "is_active": False,
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["surname"] == update_data["surname"]
        assert data["email"] == update_data["email"]
        assert data["is_active"] == update_data["is_active"]

    def test_update_current_user_partial_fields(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating current user with only some fields."""
        update_data = {
            "name": "PartialUpdate",
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_update_current_user_empty_data(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating current user with empty data fails validation."""
        update_data = {}
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_current_user_invalid_email(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating current user with invalid email fails."""
        update_data = {
            "email": "invalid-email-format",
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_current_user_as_regular_user(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test updating profile as regular user works."""
        update_data = {
            "name": "UpdatedRegularUser",
        }
        response = identity_aware_client.put_as(regular_user, "/api/v1/users/me", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_update_current_user_without_authentication(self, client: TestClient) -> None:
        """Test updating current user without authentication fails."""
        update_data = {
            "name": "ShouldFail",
        }
        response = client.put("/api/v1/users/me", json=update_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /users/me/permissions - Get current user permissions
    def test_get_current_user_permissions_as_admin(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting current user permissions as admin."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/me/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Admin should have permissions
        assert len(data) > 0

        # Check permission structure
        if data:
            permission = data[0]
            assert "id" in permission
            assert "name" in permission

    def test_get_current_user_permissions_as_regular_user(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting current user permissions as regular user."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/users/me/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Regular user may have no permissions
        assert len(data) >= 0

    def test_get_current_user_permissions_without_authentication(self, client: TestClient) -> None:
        """Test getting current user permissions without authentication fails."""
        response = client.get("/api/v1/users/me/permissions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /users/me/roles - Get current user roles
    def test_get_current_user_roles_as_admin(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting current user roles as admin."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/me/roles")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Admin should have at least the admin role
        assert len(data) > 0

        # Check role structure
        if data:
            role = data[0]
            assert "id" in role
            assert "name" in role
            assert "is_active" in role

    def test_get_current_user_roles_as_regular_user(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test getting current user roles as regular user."""
        response = identity_aware_client.get_as(regular_user, "/api/v1/users/me/roles")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Regular user may have no roles
        assert len(data) >= 0

    def test_get_current_user_roles_without_authentication(self, client: TestClient) -> None:
        """Test getting current user roles without authentication fails."""
        response = client.get("/api/v1/users/me/roles")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for PUT /users/me/password - Update current user password
    def test_update_current_user_password_valid(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, settings: BaseKwikSettings
    ) -> None:
        """Test updating current user password with valid data."""
        password_data = {
            "old_password": settings.FIRST_SUPERUSER_PASSWORD,
            "new_password": "newpassword123",
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me/password", json=password_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "email" in data

    def test_update_current_user_password_wrong_old_password(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating password with wrong old password fails."""
        password_data = {
            "old_password": "wrongoldpassword",
            "new_password": "newpassword123",
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me/password", json=password_data)

        # This should fail with some error status - let's see what the implementation returns
        assert response.status_code != HTTPStatus.OK

    def test_update_current_user_password_missing_fields(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating password with missing fields fails."""
        password_data = {
            "old_password": "somepassword",
            # Missing new_password
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/me/password", json=password_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_current_user_password_as_regular_user(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User
    ) -> None:
        """Test updating password as regular user works."""
        password_data = {
            "old_password": "regularpassword123",
            "new_password": "newregularpassword123",
        }
        response = identity_aware_client.put_as(regular_user, "/api/v1/users/me/password", json=password_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == regular_user.id

    def test_update_current_user_password_without_authentication(self, client: TestClient) -> None:
        """Test updating password without authentication fails."""
        password_data = {
            "old_password": "somepassword",
            "new_password": "newpassword123",
        }
        response = client.put("/api/v1/users/me/password", json=password_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    # Tests for GET /users/{user_id} - Get user by ID
    def test_get_user_by_id_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test getting user by ID with admin permissions."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/users/{regular_user.id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["name"] == regular_user.name
        assert data["surname"] == regular_user.surname
        assert data["email"] == regular_user.email

    def test_get_user_by_id_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting non-existent user by ID fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/users/{NONEXISTENT_USER_ID}")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_user_by_id_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User, admin_user: User
    ) -> None:
        """Test getting user by ID without admin permission fails."""
        response = identity_aware_client.get_as(regular_user, f"/api/v1/users/{admin_user.id}")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_user_by_id_without_authentication(self, client: TestClient, regular_user: User) -> None:
        """Test getting user by ID without authentication fails."""
        response = client.get(f"/api/v1/users/{regular_user.id}")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_by_id_invalid_id(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test getting user with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/invalid-id")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Tests for PUT /users/{user_id} - Update user by ID
    def test_update_user_by_id_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test updating user by ID with admin permissions."""
        update_data = {
            "name": "UpdatedByAdmin",
            "surname": "AdminUpdated",
        }
        response = identity_aware_client.put_as(admin_user, f"/api/v1/users/{regular_user.id}", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == regular_user.id
        assert data["name"] == update_data["name"]
        assert data["surname"] == update_data["surname"]

    def test_update_user_by_id_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating non-existent user by ID fails."""
        update_data = {
            "name": "ShouldFail",
        }
        response = identity_aware_client.put_as(admin_user, f"/api/v1/users/{NONEXISTENT_USER_ID}", json=update_data)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_user_by_id_empty_data(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test updating user by ID with empty data fails."""
        update_data = {}
        response = identity_aware_client.put_as(admin_user, f"/api/v1/users/{regular_user.id}", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_user_by_id_invalid_email(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test updating user by ID with invalid email fails."""
        update_data = {
            "email": "invalid-email-format",
        }
        response = identity_aware_client.put_as(admin_user, f"/api/v1/users/{regular_user.id}", json=update_data)

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_user_by_id_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User, admin_user: User
    ) -> None:
        """Test updating user by ID without admin permission fails."""
        update_data = {
            "name": "ShouldFail",
        }
        response = identity_aware_client.put_as(regular_user, f"/api/v1/users/{admin_user.id}", json=update_data)
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_update_user_by_id_without_authentication(self, client: TestClient, regular_user: User) -> None:
        """Test updating user by ID without authentication fails."""
        update_data = {
            "name": "ShouldFail",
        }
        response = client.put(f"/api/v1/users/{regular_user.id}", json=update_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_update_user_by_id_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating user with invalid ID format."""
        update_data = {
            "name": "ShouldFail",
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/invalid-id", json=update_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Tests for GET /users/{user_id}/permissions - Get user permissions
    def test_get_user_permissions_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test getting user permissions with admin permissions."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/users/{regular_user.id}/permissions")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Check permission structure if any exist
        if data:
            permission = data[0]
            assert "id" in permission
            assert "name" in permission

    def test_get_user_permissions_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting permissions for non-existent user fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/users/{NONEXISTENT_USER_ID}/permissions")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_user_permissions_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User, admin_user: User
    ) -> None:
        """Test getting user permissions without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, f"/api/v1/users/{admin_user.id}/permissions")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_user_permissions_without_authentication(self, client: TestClient, regular_user: User) -> None:
        """Test getting user permissions without authentication fails."""
        response = client.get(f"/api/v1/users/{regular_user.id}/permissions")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_permissions_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting user permissions with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/invalid-id/permissions")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Tests for GET /users/{user_id}/roles - Get user roles
    def test_get_user_roles_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test getting user roles with admin permissions."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/users/{regular_user.id}/roles")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        # Check role structure if any exist
        if data:
            role = data[0]
            assert "id" in role
            assert "name" in role
            assert "is_active" in role

    def test_get_user_roles_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test getting roles for non-existent user fails."""
        response = identity_aware_client.get_as(admin_user, f"/api/v1/users/{NONEXISTENT_USER_ID}/roles")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_user_roles_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User, admin_user: User
    ) -> None:
        """Test getting user roles without required permissions fails."""
        response = identity_aware_client.get_as(regular_user, f"/api/v1/users/{admin_user.id}/roles")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_user_roles_without_authentication(self, client: TestClient, regular_user: User) -> None:
        """Test getting user roles without authentication fails."""
        response = client.get(f"/api/v1/users/{regular_user.id}/roles")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_user_roles_invalid_id(self, identity_aware_client: IdentityAwareTestClient, admin_user: User) -> None:
        """Test getting user roles with invalid ID format."""
        response = identity_aware_client.get_as(admin_user, "/api/v1/users/invalid-id/roles")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # Tests for PUT /users/{user_id}/password - Admin password change
    def test_update_user_password_with_admin_permission(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test updating user password with admin permissions."""
        password_data = {
            "old_password": "regularpassword123",
            "new_password": "adminchangedpassword123",
        }
        response = identity_aware_client.put_as(
            admin_user, f"/api/v1/users/{regular_user.id}/password", json=password_data
        )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == regular_user.id

    def test_update_user_password_nonexistent_user(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating password for non-existent user fails."""
        password_data = {
            "old_password": "anypassword",
            "new_password": "newpassword123",
        }
        response = identity_aware_client.put_as(
            admin_user, f"/api/v1/users/{NONEXISTENT_USER_ID}/password", json=password_data
        )

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_user_password_missing_fields(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User, regular_user: User
    ) -> None:
        """Test updating user password with missing fields fails."""
        password_data = {
            "old_password": "somepassword",
            # Missing new_password
        }
        response = identity_aware_client.put_as(
            admin_user, f"/api/v1/users/{regular_user.id}/password", json=password_data
        )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_update_user_password_without_permission(
        self, identity_aware_client: IdentityAwareTestClient, regular_user: User, admin_user: User
    ) -> None:
        """Test updating user password without admin permission fails."""
        password_data = {
            "old_password": "somepassword",
            "new_password": "newpassword123",
        }
        response = identity_aware_client.put_as(
            regular_user, f"/api/v1/users/{admin_user.id}/password", json=password_data
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_update_user_password_without_authentication(self, client: TestClient, regular_user: User) -> None:
        """Test updating user password without authentication fails."""
        password_data = {
            "old_password": "somepassword",
            "new_password": "newpassword123",
        }
        response = client.put(f"/api/v1/users/{regular_user.id}/password", json=password_data)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_update_user_password_invalid_id(
        self, identity_aware_client: IdentityAwareTestClient, admin_user: User
    ) -> None:
        """Test updating user password with invalid ID format."""
        password_data = {
            "old_password": "somepassword",
            "new_password": "newpassword123",
        }
        response = identity_aware_client.put_as(admin_user, "/api/v1/users/invalid-id/password", json=password_data)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
