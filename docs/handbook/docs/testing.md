---
title: Testing
---

# Testing with kwik.testing

Kwik ships testing utilities to speed up end‑to‑end and CRUD testing against a real PostgreSQL database. The `kwik.testing` module includes:

- Scenario: a fluent builder for users, roles, and permissions
- IdentityAwareTestClient: a TestClient wrapper that authenticates as specific users
- Pytest fixtures: ready‑made DB/session/contexts and factory helpers

This page shows how to enable them and use them effectively.

## Quickstart

Prerequisites:

- Docker running locally (for Testcontainers)
- pytest installed in your environment

Enable fixtures in your test suite via `conftest.py`:

```python
# conftest.py
pytest_plugins = [
    "kwik.testing.fixtures.core_fixtures",
    "kwik.testing.fixtures.factories",
]
```

That makes these fixtures available:

- `postgres`, `settings`, `engine` (session-scoped, DB lifecycle)
- `session` (per-test, rollback isolation)
- `admin_user`, `regular_user`
- `admin_context`, `no_user_context`
- `user_factory`, `role_factory`, `permission_factory`

Tip: You can override any fixture locally in your project’s `conftest.py` if you need to customize behavior.

For a full, in-depth explanation of each fixture (scope, lifecycle, parameters, and override patterns), see the dedicated page: Testing → Fixtures.

## Database setup (Testcontainers)

`core_fixtures` starts a disposable PostgreSQL 15 container using Testcontainers and wires `BaseKwikSettings` to point to it. Schema is created at the start of the test session and dropped at the end. Tests run against a real database, not mocks.

If you prefer an existing DB, override `settings` and/or `engine` in your `conftest.py` to point at your instance.

## Scenario: fluent test data

`Scenario` lets you declare users, roles, and permissions with a chainable API and builds them in the correct order.

```python
from kwik.testing import Scenario

def test_business_flow(session, admin_user):
    scenario = (
        Scenario()
        .with_role("editor", permissions=["posts:read", "posts:write"])
        .with_user(name="john", email="john@test.com", roles=["editor"]) 
        .with_admin_user(name="alice")
        .build(session=session, admin_user=admin_user)
    )

    john = scenario.users["john"]
    editor = scenario.roles["editor"]
    assert john.id is not None
    assert editor.name == "editor"
```

Notes:

- Supplying `admin_user` to `build(...)` is required when your scenario involves roles, permissions, or admin users.
- The result gives you dictionaries for `users`, `roles`, and `permissions` by name.

## Factories: quick entities in tests

Factory fixtures wrap the `Scenario` API for concise creation:

```python
def test_role_and_user(user_factory, role_factory):
    role = role_factory(name="editor", permissions=["posts:read"]) 
    user = user_factory(name="john", roles=["editor"]) 

    assert role.name == "editor"
    assert user.email.endswith("@test.com")
```

- `user_factory(...)` returns a `User`
- `role_factory(...)` returns a `Role`
- `permission_factory(name=...)` returns a `Permission`

These use `admin_context` automatically for operations that require elevated privileges.

## IdentityAwareTestClient: authenticated requests

Wrap FastAPI’s `TestClient` to make requests “as a user” without manually handling tokens. It automatically logs in via `/api/v1/login/access-token` and caches tokens per user.

```python
from fastapi.testclient import TestClient
from kwik.testing import IdentityAwareTestClient

def test_protected_endpoint(app, admin_user):
    client = IdentityAwareTestClient(TestClient(app))

    # Perform request as admin_user
    res = client.get_as(admin_user, "/api/v1/protected")
    assert res.status_code == 200
```

Available methods mirror HTTP verbs: `get_as`, `post_as`, `put_as`, `patch_as`, `delete_as`. For public endpoints, use the wrapped client’s regular methods (e.g., `client.get("/public")`).

## Tips and best practices

- Keep fixtures lean and override locally when you need specific data or lifecycle changes.
- Use factories for readability and to avoid duplicating setup steps across tests.
- Avoid magic numbers/constants in tests to satisfy ruff rules; use named variables or fixtures.
- For faster local feedback: `pytest --disable-warnings --tb=short` or run by markers (e.g., `-m "not slow"`).
- Parallel runs: `pytest` (defaults to parallel in this repo); disable with `-n 0` when debugging.

## Related

- Settings reference: `kwik.settings.BaseKwikSettings`
- Testing utilities: `kwik.testing` (Scenario, IdentityAwareTestClient, fixtures)
