# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
