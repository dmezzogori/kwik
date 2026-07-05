# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-07-03

Kwik 2.0 makes the user identity **extensible**. Applications compose their own
user model from a mixin, register it once through a typed `Kernel`, and Kwik wires
its authentication, CRUD, routers, and testing utilities to that class — a single
`users` table, no side tables or proxying, with the user statically typed as the
app's concrete model. This is a breaking release; see the
[User model guide](https://davide.mezzogori.com/kwik/user-model/) for the full
migration walkthrough.

### Added

- **`kwik.Kernel` and `kwik.UserSchemas`** — the typed registration point for the application's user model and schemas. `Kernel[UserT: UserMixin]` validates the model and schemas, claims the process-wide slot, and exposes typed dependency callables (`get_current_user`, `get_resolved_user`, `get_user_context`) plus a typed `crud_users: CRUDUsers[UserT]`. `get_kernel()` (in `kwik.kernel`) returns the active kernel, materializing a `DefaultUser` kernel lazily for zero-config apps.
- **`kwik.UserMixin`** (`kwik.models.UserMixin`) — a pure auth mixin contributing the auth-essential columns (`id`, `name`, `surname`, `email`, `hashed_password`, `is_active`) and the `roles`/`permissions` relationships. Compose a custom user model as `class AppUser(Base, UserMixin)` with `__tablename__ = "users"`.
- **`DefaultUser`** — the built-in user model, imported lazily only when no custom kernel is registered, so zero-config applications keep working unchanged.
- **Kernel-bound router factories** — `create_login_router()`, `create_users_router()`, `create_roles_router()`, and `create_api_router(*, login=True, users=True, roles=True, permissions=True)`, each built from the kernel's model and schemas, with per-router opt-out flags.
- **`kwik.seeding.create_first_superuser(*, session, settings, **extra_fields)`** — an idempotent first-superuser battery (admin role, all permissions, superuser, role assignment) shared by production apps and Kwik's own `admin_user` fixture; `extra_fields` supports custom models with non-null columns.
- **Custom-model testing support** — `Scenario` and `user_factory` accept `extra_fields`, validated through the registered registration schema; `ScenarioResult.passwords` exposes the plaintext passwords a build used, and `IdentityAwareTestClient.register_passwords(...)` consumes them to authenticate scenario users.
- **`AutoCRUD(model=...)`** — subclasses may pass the model explicitly (required when the subclass is itself generic over the model, e.g. the kernel-owned users CRUD); otherwise the model is inferred from the generic parameters as before.
- **Custom-user test session and typing contract** — a separate `tests_custom_user/` pytest session exercises the mechanism against a custom model, and `tests_custom_user/test_typing_contract.py` pins the typing guarantee with `typing.assert_type` under a scoped pyright CI step.

### Security

- **First-superuser seeding has insecure defaults** — `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` default to `admin@example.com` / `admin`, and `create_first_superuser` grants the seeded user **every** permission. Production deployments **must** set `KWIK_FIRST_SUPERUSER` / `KWIK_FIRST_SUPERUSER_PASSWORD` before first startup. See the [User model guide](https://davide.mezzogori.com/kwik/user-model/#seeding-the-first-superuser).

### Changed

- **`Context` is now bounded** — its type parameter changed from a fixed constraint to `Context[U: UserMixin | None]`, making `Context[AppUser]` legal. The `UserCtx` / `MaybeUserCtx` / `NoUserCtx` aliases re-point onto `UserMixin`.
- **`current_user` / `resolved_user` are typed against `UserMixin`** — the module-level dependencies resolve the active kernel at request time; the kernel's `get_current_user` / `get_resolved_user` are typed `-> UserT` for app-side aliases.
- **AutoCRUD audit-column validation relaxed** — the check now accepts any Context whose user type argument is non-optional (instead of requiring the exact `UserCtx`), so app-defined `Context[AppUser]` CRUD classes pass while nullable-user contexts still fail loudly.

### Removed

All removals below are **breaking changes** requiring code updates. See the migration guide.

- **`kwik.api_router` singleton and `kwik.api.api`** — assemble routers via `kernel.create_api_router(...)` instead (each built-in router is individually opt-out-able).
- **Module-level `users_router` / `login_router` / `roles_router`** — replaced by the kernel's router factories.
- **`kwik.crud.crud_users` singleton** — use `kernel.crud_users` (or `get_kernel().crud_users` for the default model), typed `CRUDUsers[UserT]`.
- **`kwik.models.User` export and the concrete `User` model** — compose your own `AppUser(Base, UserMixin)`; there is no top-level `User` name.
- **Audit `UserMixin` renamed to `UserTrackingMixin`** — the audit-trail mixin (`creator_user_id`, `last_modifier_user_id`) is now `kwik.models.UserTrackingMixin` (no deprecation alias); `UserMixin` now names the new auth mixin. `RecordInfoMixin` composition is unchanged.

### Migration

- Full migration walkthrough — including the single-Alembic-migration recipe for collapsing a 1.x two-table user pattern — is published in the handbook: **[Extending the User model](https://davide.mezzogori.com/kwik/user-model/)**.

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
