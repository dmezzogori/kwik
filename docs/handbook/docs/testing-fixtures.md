---
title: Testing Fixtures
---

# Testing Fixtures

Kwik provides reusable pytest fixtures for spinning up a real PostgreSQL database, creating sessions and contexts, and seeding common users/roles/permissions. This page documents each fixture in detail and shows how to override them when needed.

To enable fixtures in your test suite, add this to `conftest.py`:

```python
pytest_plugins = [
    "kwik.testing.fixtures.core_fixtures",
    "kwik.testing.fixtures.factories",
]
```

Fixtures are designed to be safe defaults you can override locally. Use your own `conftest.py` to replace or tweak any fixture documented here.

## Core fixtures (core_fixtures)

### postgres (session)

Starts a disposable PostgreSQL 15 container with Testcontainers. It exposes host/port and credentials for other fixtures. Lifecycle: container lives for the whole pytest session and is cleaned up automatically.

- Image: `postgres:15-alpine`
- Credentials: user `postgres`, password `root`, db `kwik_test`
- Purpose: provide a clean, isolated DB for each test session

Override: if you don’t want a container, override `settings` (or `engine`) in your project to point to a running DB and remove the dependency on `postgres`.

### settings (session)

Creates `kwik.settings.BaseKwikSettings` configured to use the `postgres` container’s connection info. This is the single source of truth for DB connectivity across the fixtures.

Provided values:

- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_DB = "kwik_test"`
- `POSTGRES_USER = "postgres"`
- `POSTGRES_PASSWORD = "root"`

Override: Provide your own `settings` fixture returning `BaseKwikSettings` (or your subclass) to point to an external DB or adjust credentials.

### engine (session, autouse)

Creates a SQLAlchemy engine from `settings`, then initializes the schema by calling `Base.metadata.create_all(...)` at session start. At the end of the session, it drops all tables and disposes the engine.

- Scope: session-wide, autouse
- DDL: create_all on start; drop_all on finish

Override: If your project requires Alembic migrations instead of `create_all`, override `engine` and run migrations in your custom fixture before yielding the engine.

### admin_user (session, autouse)

Creates a shared admin user and ensures an `admin` role exists with all permissions assigned. The user’s email and password come from `BaseKwikSettings.FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD`.

What it does:

- Creates an admin user (active)
- Creates an `admin` role
- Iterates over all `kwik.core.enum.Permissions` entries and creates corresponding permissions
- Assigns all permissions to the `admin` role
- Assigns the admin user to the `admin` role

Usage: import and use directly in tests to impersonate via the IdentityAwareTestClient or for CRUD scenarios that need elevated privileges.

### regular_user (session, autouse)

Creates a shared, active non-admin user with:

- Email: `regular@example.com`
- Password: `regularpassword123`

This user is useful for testing authorization boundaries and non-privileged flows. IdentityAwareTestClient recognizes this user and logs in with the correct password automatically.

### session (function)

Provides a DB session per test with rollback semantics for isolation. It uses `kwik.database.session_scope(session=session, commit=False)`, yielding the session and rolling back at the end of the test.

- Scope: function (per test)
- Isolation: changes rolled back at the end of each test

Tip: Use this session to build scenarios and CRUD operations without leaking state across tests.

### admin_context (function)

Provides a `kwik.crud.Context` bound to the function-scoped `session` and the session-scoped `admin_user`. Use this for CRUD operations requiring permissions or role assignments.

### no_user_context (function)

Provides a `kwik.crud.Context` bound to the function-scoped `session` with `user=None`. Use this for CRUD operations that must run without an authenticated user (e.g., public creation paths).

## Factory fixtures (factories)

Factory fixtures offer concise helpers built on top of the `Scenario` fluent API. They hide boilerplate and pick the right context automatically.

### user_factory (function)

Creates a `User` with configurable attributes. Arguments:

- `name: str = "testuser"`
- `surname: str = "testsurname"`
- `email: str | None = None` (defaults to `"{name.lower()}@test.com"`)
- `password: str = "testpassword123"`
- `is_active: bool = True`
- `admin: bool = False`
- `roles: list[str] | None = None`

Behavior:

- If `admin` is True or `roles` are provided, creation uses `admin_context` (required for role assignments and admin users)
- Otherwise, user is created with a context where `user=None`

Example:

```python
def test_user_creation(user_factory):
    admin = user_factory(name="admin", admin=True)
    editor = user_factory(name="john", roles=["editor"])  # role must exist
    assert admin.is_active is True
    assert editor.email.startswith("john@")
```

### role_factory (function)

Creates a `Role` and assigns optional permissions.

- `name: str = "test_role"`
- `is_active: bool = True`
- `permissions: list[str] | None = None`

Example:

```python
def test_role_factory(role_factory):
    role = role_factory(name="editor", permissions=["posts:read", "posts:write"]) 
    assert role.name == "editor"
```

### permission_factory (function)

Creates a `Permission` by name.

- `name: str = "test_permission"`

Example:

```python
def test_permission_factory(permission_factory):
    perm = permission_factory(name="posts:read")
    assert perm.name == "posts:read"
```

## Overriding fixtures

You can override any fixture in your own `conftest.py`. Common patterns:

### Use an existing database (no container)

```python
import pytest
from kwik.settings import BaseKwikSettings

@pytest.fixture(scope="session")
def settings() -> BaseKwikSettings:
    return BaseKwikSettings(
        POSTGRES_SERVER="127.0.0.1",
        POSTGRES_PORT="5432",
        POSTGRES_DB="kwik_test",
        POSTGRES_USER="postgres",
        POSTGRES_PASSWORD="root",
    )
```

### Run migrations instead of create_all

```python
import pytest
from sqlalchemy.engine import Engine
from kwik.database import create_engine

@pytest.fixture(scope="session", autouse=True)
def engine(settings) -> Engine:  # type: ignore[override]
    engine = create_engine(settings)
    # run_alembic_migrations(engine)
    try:
        yield engine
    finally:
        engine.dispose()
```

### Seed custom data or modify users

```python
import pytest
from kwik.crud import Context, crud_users
from kwik.schemas import UserRegistration
from kwik.testing.fixtures.core_fixtures import admin_user as base_admin_user

@pytest.fixture(scope="session", autouse=True)
def admin_user(engine, settings, base_admin_user):  # type: ignore[override]
    # Use the base admin_user fixture and add extra users/data
    _ = base_admin_user
    # create additional seed data here if needed
    return _
```

## Concurrency and performance

Running tests in parallel (e.g., `pytest -n auto`) will create session-scoped fixtures per worker process. That can mean multiple PostgreSQL containers in parallel. This is typically fine; just consider resource usage. If you need a single container, disable parallelization.

The `session` fixture isolates test data with rollbacks. For heavier tests that require commit semantics, perform explicit commits as needed and ensure cleanup in test teardown.

## Interaction with IdentityAwareTestClient

The IdentityAwareTestClient knows how to authenticate these users:

- `regular_user` uses the password `regularpassword123`
- the admin user uses `settings.FIRST_SUPERUSER_PASSWORD`
- unknown users default to `testpassword123`

This aligns with fixture defaults so authenticated requests work out of the box.

## Troubleshooting

- “Failed to connect to DB”: ensure Docker is running or override `settings` to use an existing DB.
- “Permission not found” during `Scenario.build`: make sure you passed `admin_user` and that roles/permissions exist or are created by the scenario.
- Excess containers with xdist: reduce workers or override fixtures to use a shared DB.

