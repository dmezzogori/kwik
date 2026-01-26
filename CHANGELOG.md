# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
