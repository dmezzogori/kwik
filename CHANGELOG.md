# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.13.0] - 2026-10-11

### Changed

- **BREAKING: new passwords must have at least 12 characters.** `NewPassword` now enforces `PASSWORD_MIN_LENGTH` (default 12, configurable between 1 and 72) on top of bcrypt's 72-byte bound, so `UserRegistration.password`, `UserPasswordChange.new_password`, `AdminPasswordReset.new_password` and every application schema reusing `NewPassword` refuse shorter passwords with a 422. The rule is length only, with no composition rules, following NIST SP 800-63B. `POST /login/reset-password` now validates its `password` as `NewPassword` (it was a bare `str`). **Existing accounts are unaffected**: verifying a password (login, `old_password`) stays unconstrained. Seeds and scripts that create accounts from configuration, such as the first superuser, validate with `context={"password_policy": False}` to skip the minimum; kwik's `admin_user` fixture does, so the development default `FIRST_SUPERUSER_PASSWORD="admin"` keeps working (teban #302).
- **BREAKING: an inactive role is held by no one.** `crud_users.has_permissions` (and so every `has_permission` gate), `has_roles`, `get_roles`, `get_permissions` and `User.permissions` count active roles only, and `GET /users/me/roles` and `GET /users/me/permissions` follow. Deactivating a role is a quick way to take it, and its permissions, from every user who holds it. `User.roles` and the role-management reads (`Role.users`, `GET /roles/{id}/users`) still list assignments, active or not. The permission check's aggregate query joins `roles`; it is still one round-trip (teban #908).
- **BREAKING: a starved connection-pool checkout fails after 10 s instead of 30 s.** See `POSTGRES_POOL_TIMEOUT` below (teban #777).
- **A failed commit is now a 5xx.** The commit used to run after the response had been sent, so its failure reached the client as a success; it now runs before the response goes out.

### Added

- **`kwik.api.build_api_router(exclude=...)`** — kwik's built-in routes as one router, minus the `(METHOD, path)` pairs an application overrides or withdraws. An override registered first wins dispatch, but without the exclusion the application keeps a second handler, and OpenAPI documents kwik's handler instead of the override. It raises `ValueError` when a pair matches no route, or matches only some of a route's methods, so a kwik upgrade that moves a route fails at import rather than silently bringing the unguarded route back. `kwik.api.api_router` is now `build_api_router()`, with the same routes in the same order. The handbook documents the override pattern (teban #378, #302).
- **`PASSWORD_MIN_LENGTH`** setting, **`kwik.security.configure_password_policy`** / **`password_min_length`**, and **`kwik.core.DEFAULT_PASSWORD_MIN_LENGTH`** — the password policy above. `Kwik` configures it from settings at construction; processes that never build a `Kwik` app keep the default.
- **`POSTGRES_POOL_SIZE`** (10), **`POSTGRES_MAX_OVERFLOW`** (20) and **`POSTGRES_POOL_TIMEOUT`** (10.0 s) settings, previously hardcoded in `create_engine` (the timeout was SQLAlchemy's 30 s). A request finding the pool exhausted used to hold its thread for 30 s and then fail anyway, usually after the proxy had given up. **`kwik.database.warn_if_pool_exceeds_connections`** runs at startup and logs a warning when `BACKEND_WORKERS × (POSTGRES_POOL_SIZE + POSTGRES_MAX_OVERFLOW)` exceeds `POSTGRES_MAX_CONNECTIONS`, since each worker has its own pool. The handbook's new Database page gives the reasoning and the sizing rule (teban #777).
- **`BACKEND_GRACEFUL_TIMEOUT`** setting (30 s), passed to gunicorn as `graceful_timeout`, and **`kwik.applications.uvicorn.GRACEFUL_SHUTDOWN_MARGIN`** (5 s). Keep the container's stop grace period above it (see Fixed).

### Fixed

- **Writes are committed before the response is sent.** With FastAPI 0.140, the commit in the session dependency's `yield` teardown ran after the response had been sent, so a client acting on the response at once (a sign-in followed by `GET /me`, a create followed by a navigation) could read the database before the write was committed. `Kwik` now installs `_commit_session` app-wide with `scope="function"`: it shares the request's session and commits after the endpoint returns and the response is serialized, before the status line goes out. If the endpoint raises, nothing is committed. The request-scoped session still owns the lifecycle: it rolls back on error, commits writes made later (streaming bodies, background tasks) and closes after the response. Every route is covered, with no change to endpoint code (teban #823). Consequences for applications: session `after_commit` hooks (such as emails queued "after the transaction commits") now fire before the response is sent, so tests that made a request and then committed or rolled back the test session themselves to trigger or suppress such a hook must be rewritten; and a route that declares `Depends(_get_session, scope="function")` itself now also gets the app-wide request-scoped session instance, which `_commit_session` commits (an unused session holds no connection, so this costs nothing at runtime, but an override of `_get_session` runs twice on such a route).
- **Open streams are cancelled before gunicorn kills the worker on restart.** gunicorn's `graceful_timeout` was left at its default and uvicorn's `timeout_graceful_shutdown` was unset, so uvicorn waited on open streaming responses until gunicorn SIGKILLed the worker, and the streams' cleanup (for example a lease release in a `finally`) never ran. `KwikUvicornWorker` now sets `timeout_graceful_shutdown` to gunicorn's `graceful_timeout` minus `GRACEFUL_SHUTDOWN_MARGIN`, never below 1 s, so open streams are cancelled and clean up in time (teban #757). The container runtime's stop grace period must exceed `BACKEND_GRACEFUL_TIMEOUT` (Docker's default is 10 s: set `stop_grace_period`, for example `40s` with the 30 s default), otherwise the runtime kills the container before uvicorn's deadline and the cleanup still never runs.

### Testing

- The API test client joins an outer transaction in `create_savepoint` mode, so the per-request commits release a SAVEPOINT and each test's writes are still rolled back. Applications whose test session overrides `_get_session` with a plain session must do the same, or their tests start committing for real.

## [1.12.0] - 2026-07-28

### Changed

- **BREAKING: passwords longer than 72 UTF-8 bytes are now rejected instead of silently truncated.** `bcrypt` 5.0.0 raises `ValueError` past that bound rather than discarding the excess, as every earlier version did. Passwords being *set* are validated at the schema boundary (`UserRegistration.password`, `UserPasswordChange.new_password`, `AdminPasswordReset.new_password`) and re-checked in `get_password_hash`. **Existing hashes are unaffected** — the `$2b$` format and cost 12 default are unchanged, so no migration or forced password reset is required. Any account whose plaintext secret exceeded 72 bytes was already being verified against a truncated value and will now fail to log in; such accounts need a password reset.
- **`old_password` is deliberately left unconstrained.** An account created under bcrypt <5.0.0 may hold a longer secret; rejecting it at validation time would turn a failed login into a confusing 422.
- **BREAKING: six dependencies moved from exact pins to compatible ranges** — `aiofiles`, `bcrypt`, `fastapi[standard]`, `gunicorn`, `httptools`, `psycopg2-binary`. Exact pins meant a consumer could not absorb a security patch to any of them without waiting on a kwik release. kwik's own `uv.lock` still pins exact versions for reproducible CI.
- **Migrated off `uvicorn.workers`**, deprecated since uvicorn 0.30 and slated for removal, to the standalone `uvicorn-worker` package. `KwikUvicornWorker` behaves identically; only the import changed.

### Added

- **`kwik.core.BCRYPT_MAX_PASSWORD_BYTES`** — the 72-byte bound, shared by the schemas and the hashing code. It lives in `core` because `kwik.security` imports `kwik.schemas`, so the constant cannot sit in either without a cycle.
- **`kwik.schemas.NewPassword`** — the annotated password type, exported so downstream schemas that collect a password and forward it to kwik can apply the same bound at *their* request boundary. Without it the constraint fires only when kwik builds its own schema deeper in the call stack, where a Pydantic `ValidationError` surfaces as a 500 rather than a 422.
- **`kwik.exceptions.users.PasswordTooLongError`** — a 422 `KwikError` raised by `get_password_hash`, so callers bypassing schema validation get a typed error instead of a bare `ValueError`.

### Security

- **bcrypt 4.0.1 → >=5.0.0** — clears the pin 1.10.0 recorded as "remains pinned (not flagged)". `passlib` is absent from kwik, so the well-known `bcrypt.__about__` incompatibility never applied here.
- **psycopg2-binary 2.9.10 → >=2.9.12** — binary wheels move off end-of-life OpenSSL 1.1.1w to 3.5.6, and libpq 16.0 → 17.9.
- **httptools 0.6.4 → >=0.8.0** — fixes `parse_url` truncating URLs past 64KB (`uint16_t` offset wrap), which reaches `scope["path"]`. kwik forces the httptools parser, so this is on the request path.
- **fastapi 0.138.0 → >=0.140.7** and **gunicorn 23.0.0 → >=26.0.0** — no advisories outstanding at the previous pins; both carry upstream hardening. gunicorn 26 removes the eventlet worker (unused here) and adds a control socket.

## [1.11.0] - 2026-07-27

### Changed

- **`User.roles` and `Role.permissions` are now `lazy="selectin"`** — loading any set of users (or roles) batch-loads the related roles (permissions) in one additional query per result set instead of one query per row. This eliminates the recurring N+1 class on user-listing read paths in downstream apps with no consumer code changes.
- **`crud_users.has_permissions` runs a single aggregate query** over `users_roles`/`roles_permissions` instead of traversing lazy ORM collections, so permission checks cost one round-trip regardless of relationship loading state. Detached users fall back to their already-loaded collections. Signature unchanged.
- **`Role.user_count` is now a deferred column property** — casual `Role` loads (including the roles reached through `User.roles`) no longer pay the correlated `count(users_roles.id)` subquery. The roles CRUD read paths (`get`/`get_if_exist`/`get_multi`) undefer it explicitly, so `RoleProfile.user_count` serialization stays query-free.

### Fixed

- **Viewonly RBAC collections no longer go stale within a session** — every `crud_roles` association mutation (`assign_user`, `remove_user`, `assign_permission`, `remove_permission`, `remove_all_users`, `remove_all_permissions`) now expires the affected viewonly collections (`user.roles`, `role.users`, `role.permissions`, `Role.user_count`). Eager-loaded collections read after a mutation reload fresh data instead of serving the pre-mutation snapshot.

### Added

- **`AutoCRUD.select_options`** — class-level loader options applied on the read paths (`get`/`get_if_exist`/`get_multi`), e.g. for undeferring column properties the read schema serializes.
- **`kwik.testing.assert_max_queries(session, n)`** — context manager that captures every SQL statement executed in the block and fails with the statement list when the count exceeds the limit; yields the captured statements. One-line N+1 regression tests for kwik apps.

## [1.10.0] - 2026-06-25

### Changed

- **BREAKING: `generate_password_reset_token` now requires a `password_hash` keyword** — signature is now `generate_password_reset_token(*, email: str, settings: BaseKwikSettings, password_hash: str) -> str`. The token embeds a `pwd` fingerprint claim (`sha256(password_hash).hexdigest()[:16]`) alongside `sub`/`exp` (48h)/`nbf`, so any outstanding reset token is invalidated the moment the user's password changes.
- **BREAKING: `verify_password_reset_token` now requires a CRUD `context`** — signature is now `verify_password_reset_token(token, settings, context) -> str | None`. It looks up the user by the token's `sub`, recomputes the fingerprint from the current `hashed_password`, and returns the email only when the fingerprint matches **and** the user is active; otherwise `None`. JWT errors return `None` instead of raising.
- **BREAKING: `POST /login/reset-password` is now unauthenticated** — the endpoint dependency changed from `UserContext` to `NoUserContext` so a logged-out user holding a valid reset token can complete the flow (it previously returned `401`). Request body (`{token, password}`) and response (`{"msg": ...}`) are unchanged.

### Security

- **FastAPI 0.135.2 → 0.138.0**, pulling fixed transitives **Starlette 1.3.1** and **python-multipart 0.0.32**.
- Cleared the remaining Dependabot alerts via lockfile upgrade: **urllib3** 2.6.3 → 2.7.0, **PyJWT** 2.12.1 → 2.13.0, **pydantic-settings** 2.13.1 → 2.14.2, **idna** → 3.15, **pytest** 9.0.2 → 9.1.1.
- **CI:** bumped `actions/checkout` 6 → 7 (Dependabot #35). `bcrypt==4.0.1` remains pinned (not flagged).

## [1.9.0] - 2026-04-01

### Changed

- **FastAPI upgraded from 0.116.1 to 0.135.2** — Includes 2x JSON response performance (Pydantic/Rust serialization), SSE support, streaming JSON Lines, dependency scopes, and Starlette 1.0.0 compatibility.
- **Upstream breaking changes**:
  - FastAPI security classes now return `401` instead of `403` when credentials are missing (since FastAPI 0.122.0).
  - Strict `Content-Type` checking for JSON requests is now enabled by default (since FastAPI 0.132.0). Disable with `strict_content_type=False` if needed.

### Security

- Resolved 12 Dependabot security alerts (6 high, 5 medium, 1 low):
  - **PyJWT** 2.10.1 → 2.12.1 — accepts unknown `crit` header extensions (high)
  - **python-multipart** 0.0.20 → 0.0.22 — arbitrary file write via non-default config (high)
  - **urllib3** 1.26.20 → 2.6.3 — decompression-bomb bypass, unbounded decompression chain, highly compressed data handling (high)
  - **starlette** 0.47.2 → 1.0.0 — O(n²) DoS via Range header merging (high)
  - **requests** 2.32.4 → 2.33.1 — insecure temp file reuse (medium)
  - **virtualenv** 20.31.2 → 21.2.0 — TOCTOU in directory creation (medium)
  - **filelock** 3.18.0 → 3.25.2 — TOCTOU symlink vulnerabilities (medium)
  - **Pygments** 2.19.2 → 2.20.0 — ReDoS via GUID matching (low)

### Fixed

- Updated ruff pre-commit hook from v0.12.7 to v0.15.8 to match project dependency.
- Fixed new ruff lint findings (RUF059 unused unpacked variables, E501 line length) in test files.

## [1.7.0] - 2026-03-18

### Added

- **Admin Password Reset**: New `PUT /users/{user_id}/reset-password` endpoint for admin-initiated password resets without requiring the old password. Protected by new `password_reset` permission.
- **`password_reset` permission**: New built-in permission in `Permissions` enum for controlling access to admin password reset functionality.
- **`AdminPasswordReset` schema**: New Pydantic schema with a single `new_password` field for the admin reset endpoint.

## [1.4.0] - 2026-02-20

### Changed

- **BREAKING: Permission naming convention** — Renamed all built-in permission enum members from `{domain}s_management_{action}` to `{domain}_{action}` for consistency with downstream applications:
  - `users_management_create/read/update/delete` → `user_create/read/update/delete`
  - `roles_management_create/read/update/delete` → `role_create/read/update/delete`
  - `permissions_management_create/read/update/delete` → `permission_create/read/update/delete`
  - `password_management_update` removed — admin password endpoint now uses `user_update`
- Updated documentation examples to reflect new `{domain}_{action}` naming convention.

## [1.3.2] - 2026-01-26

### Fixed

- **Idempotent Test Fixtures**: Made `admin_user` and `regular_user` test fixtures idempotent for multi-conftest scenarios. Fixtures now check if users exist before creating them, preventing `UniqueViolation` errors when multiple conftest files define session-scoped user fixtures.

## [1.3.1] - 2025-09-10

### Fixed

- **Dependency Issue**: Fixed missing `testcontainers` and `pytest` dependencies that prevented users from importing `kwik.testing` fixtures. Moved `testcontainers>=4.0.0` and `pytest>=8.0.0` from dev dependencies to main dependencies to ensure proper availability for testing infrastructure.

## [1.3.0] - 2025-09-09

### Added

- **Enhanced Testing Infrastructure**: Complete overhaul of the testing system for improved developer experience
  - **Fluent Scenario Builder**: Clean test data creation with `Scenario().with_user(admin=True).with_posts(5).build()` API
  - **Identity-Aware TestClient**: Test authentication seamlessly with `client.get_as(user, "/protected")` 
  - **Performance Test Suite**: Baseline performance metrics and parallel test execution setup
  - **Enhanced Fixtures**: Centralized, reusable test fixtures and factories for consistent test patterns
  - **100% Test Coverage**: All existing tests migrated and enhanced while maintaining complete coverage

### Changed

- **Developer Experience**: Significantly improved test creation speed and debugging capabilities
- **Test Performance**: Parallel test execution with pytest-xdist for faster development cycles  
- **Documentation**: Comprehensive testing documentation with practical examples and best practices
- **Project Management**: Migrated development roadmap from static markdown to Linear project management with tracking, dependencies, and milestones

### Improved

- **Test Reliability**: Enhanced test isolation and session management for more stable test runs
- **Code Quality**: Improved test patterns and factory implementations for better maintainability
- **Framework Foundation**: Solid testing infrastructure ready for all future Kwik v1.x development

### Technical Details

- Added `src/kwik/testing/` package with scenario builder, identity-aware client, and fixture utilities
- Enhanced pytest configuration with parallel execution and coverage optimization
- Comprehensive test suite covering CRUD operations, API endpoints, dependencies, and framework components

## [1.2.1] - 2025-08-21

### Security

- **CRITICAL FIX**: Removed context router endpoints (`/context/settings`, `/context/session`) that exposed sensitive configuration data including JWT secret keys, database credentials, and other application secrets to unauthenticated users.

### Removed

- **Context Router**: Completely removed `src/kwik/api/endpoints/context.py` and all references to prevent accidental exposure of sensitive data.
- **Development Endpoints**: Removed debug/development endpoints that were inadvertently included in production builds.

### Migration Notes

- **Breaking Change**: If your application relied on `/api/v1/context/settings` or `/api/v1/context/session` endpoints, they are no longer available.
- **Immediate Action**: Update to this version immediately if using Kwik 1.2.0 in any production environment.
- **Security Audit**: Review your logs for any unauthorized access to `/api/v1/context/*` endpoints.

## [1.2.0] - 2025-08-20

### Added

- **Configurable Upload Directory**: Added `UPLOADS_DIR` setting to `BaseKwikSettings` with default `"./uploads"` for flexible file storage configuration.
- **Enhanced File Upload Security**: Implemented robust path traversal protection using `pathlib.Path.resolve()` and `relative_to()` methods.
- **Storage Abstraction**: File upload function now returns relative paths for better storage abstraction and portability.

### Changed

- **File Upload Location**: Default upload directory changed from absolute `/uploads` to relative `./uploads` for better cross-environment compatibility.
- **Improved Performance**: Increased file upload chunk size from 1KB to 64KB (64x improvement) for better handling of large files.
- **Enhanced Security**: Replaced brittle string-based path validation with robust pathlib-based directory traversal prevention.
- **Better Error Handling**: Path traversal attempts now raise clear `ValueError` exceptions with descriptive messages.

### Migration Guide

**For users who need the previous absolute path behavior:**
- Set the environment variable `KWIK_UPLOADS_DIR="/uploads"` to maintain the old behavior.
- Alternatively, configure `UPLOADS_DIR="/uploads"` in your settings class.

**API Compatibility:**
- The `store_file` function signature remains unchanged for backward compatibility.
- Return value now includes relative paths instead of absolute paths for better storage abstraction.
- Optional `settings` parameter added but defaults to backward-compatible behavior when not provided.

## [1.1.1] - 2025-08-19

### Changed

- Documentation updated to clarify current synchronous SQLAlchemy 2.x implementation (async support planned for future).

### Removed

- Unused `asyncpg` dependency to reduce install footprint and eliminate confusion about async vs sync implementation.

## [1.1.0] - 2025-01-19

### Added

- Unified `ListQuery` dependency combining pagination, sorting, and filtering for list endpoints.
- Sorting and filtering now supported on users/roles/permissions endpoints via query params.

### Changed

- Default stable ordering applied to listings (primary key ascending) when no `sorting` is provided.
- Invalid sort/filter fields now return HTTP 400 with a clear error message.

## [1.0.0] - 2025-01-18

### Added

- **Comprehensive API Test Suite:** Complete test coverage for all API endpoints including users, roles, permissions, login, and authentication flows.
- **Enhanced Test Fixtures:** Test fixtures with session management, admin user creation, and user impersonation capabilities.
- **Security Testing:** Comprehensive tests for JWT token handling, password verification, and security utilities.
- **CRUD Testing:** Full coverage of create, read, update, delete, and relationship management operations.
- **Application Seeding:** Seeding capability for development and testing environments with initial data setup.
- **Extensible Settings System:** New settings system supporting multiple configuration sources (environment variables, JSON/YAML files, programmatic configuration).
- **Schema Validation Improvements:** AtLeastOneFieldMixin for role and user update schemas to enforce validation requirements.
- **Annotated Types:** Enhanced schemas using annotated types for better type safety and validation.
- **Error Handling:** Proper HTTP status codes (409 CONFLICT for duplicate entities).
- **Pre-commit Integration:** Pre-commit job in CI workflow for automated code quality enforcement.
- **Dependabot Configuration:** Automated dependency update management.
- **Comprehensive Docstrings:** Hundreds of docstrings added across modules, classes, functions, and methods.
- **MkDocs Configuration:** Enhanced documentation website with improved configuration and organization.
- **100% Test Coverage:** Complete test coverage achieved for the `utils` module.

### Changed

- **Pydantic V2 Migration:** Full migration to Pydantic V2 with updated validators and eliminated deprecation warnings.
- **Python 3.12 Upgrade:** Framework migrated to Python 3.12 with modern generic type syntax (PEP 695).
- **SQLAlchemy 2.0 Migration:** Comprehensive migration to SQLAlchemy 2.0 with modernized database layer, updated models, CRUD operations, and session management.
- **CRUD Layer Consolidation:** Applied entity ownership principle, merged `CRUDBase` into `AutoCRUD`, simplified class hierarchy.
- **API Endpoint Consolidation:** Consolidated user-related API endpoints for better RESTful design.
- **Pagination System:** Modernized pagination system for improved performance and usability.
- **Application Initialization:** Enhanced Kwik application initialization and lifespan management.
- **Logging System:** Integrated Loguru for enhanced logging functionality with color-coded formatting.
- **Documentation Updates:** Updated README and documentation to reflect v1.0 release and production readiness.
- **Test Directory Structure:** Moved tests directory to project root following standard Python project structure.
- **Schema Structure:** Simplified schema structure by removing redundant base classes and fields.

### Fixed

- **Test Failures:** Resolved multiple pytest test failures and improved test reliability.
- **Linting Issues:** Fixed numerous linting errors including type annotations, code formatting, and style compliance.
- **Database Connection Handling:** Improved database connection management and session handling.
- **Circular Import Issues:** Resolved critical circular import problems blocking framework startup.
- **IntegrityError Fixes:** Fixed creator_user_id NOT NULL constraint issues in tests.
- **Import Path Corrections:** Updated import paths for models, mixins, and security utilities.
- **Code Quality:** Major code quality improvements with 25% reduction in linting errors.

### Removed

- **Unused Dependencies:** Removed unused packages like `requests` and `bump-pydantic`.
- **Dead Code Cleanup:** Removed significant amount of unused code including old logging system, soft delete patterns, and various utility modules.
- **Obsolete Components:** Removed unused `AutoRouter` class, obsolete middleware, and deprecated infrastructure.
- **Legacy Systems:** Removed dead KwikSession/KwikQuery infrastructure and old session management utilities.
- **Outdated Documentation:** Removed outdated documentation files and tutorial content.
- **Redundant Code:** Removed unused role association methods, obsolete test utilities, and redundant schema components.
- **Settings Cleanup:** Removed obsolete settings like ENABLE_SOFT_DELETE, USERS_OPEN_REGISTRATION, and WEBSERVICE configurations.

### Security

- **Test Database Migration:** Replaced Docker-based test database setup with `testcontainers`, eliminating security vulnerabilities from `subprocess` calls.
- **Password Hashing Migration:** Migrated from unmaintained `passlib` to direct `bcrypt` implementation for enhanced security.
- **JWT Library Migration:** Replaced unmaintained `python-jose` with `PyJWT` for secure JSON Web Token handling.
