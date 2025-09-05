"""
Enhanced testing utilities for Kwik framework.

This module provides utilities for creating test scenarios and enhanced
test clients that simplify testing of Kwik-based applications.

Key Components:
- Scenario: Fluent API for creating complex test scenarios with users, roles, and permissions
- IdentityAwareTestClient: Test client with built-in authentication context switching

Example usage:
    from kwik.testing import Scenario, IdentityAwareTestClient

    # Create a test scenario
    scenario = (Scenario()
               .with_user(name="john", email="john@test.com", roles=["editor"])
               .with_user(name="jane", admin=True)
               .with_role("editor", permissions=["posts:read", "posts:write"])
               .build(session=session, admin_user=admin_user))

    # Use identity-aware test client
    client = IdentityAwareTestClient(test_client)
    response = client.get_as(scenario.users["john"], "/api/protected")
"""

from __future__ import annotations

from .client import IdentityAwareTestClient
from .fixtures import permission_factory, role_factory, user_factory
from .scenario import Scenario, ScenarioResult

__all__ = [
    "IdentityAwareTestClient",
    "Scenario",
    "ScenarioResult",
    "permission_factory",
    "role_factory",
    "user_factory",
]
