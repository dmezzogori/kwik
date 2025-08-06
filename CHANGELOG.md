# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Road to v2.0.0

### Security

- **Test Database Migration to Testcontainers:** Replaced the Docker-based test database setup with `testcontainers`. This eliminates security vulnerabilities associated with `subprocess` calls and provides better test isolation.
- **Password Hashing Migration:** Migrated from the unmaintained `passlib` library to a direct implementation using `bcrypt`. This enhances security and ensures the project uses actively maintained cryptography libraries.
- **JWT Library Migration:** Replaced the unmaintained `python-jose` with `PyJWT` for handling JSON Web Tokens. This addresses security concerns and deprecation warnings.

### Core Refactoring & Modernization

- **Pydantic V2 Migration:** Completed the full migration to Pydantic V2, including updating all validators and eliminating deprecation warnings.
- **Python 3.12 Upgrade:** Migrated the entire framework to Python 3.12, adopting modern generic type syntax (PEP 695).
- **Extensible Settings System:** Implemented a new, extensible settings system that supports multiple configuration sources (environment variables, JSON/YAML files, and programmatic configuration) and allows for custom settings.
- **CRUD Layer Refactoring:**
    - Consolidated the CRUD layer by applying the entity ownership principle, removing many-to-many relationship files and centralizing logic within the primary entity's CRUD module.
    - Merged the abstract `CRUDBase` into `AutoCRUD`, simplifying the class hierarchy.
- **API and Routing Improvements:**
    - Consolidated user-related API endpoints for better RESTful design.
    - Modernized the pagination system.
    - Removed the unused `AutoRouter` class.
- **Code Cleanup:**
    - Removed a significant amount of dead and unused code, including the old logging system, soft delete patterns, and various utility modules.
    - Refactored and cleaned up imports and type hints across the codebase.

### Testing & CI/CD

- **Pre-commit Integration:** Added a `pre-commit` job to the CI workflow to enforce code quality standards automatically.
- **Increased Test Coverage:** Significantly increased test coverage, reaching 100% for the `utils` module and fixing numerous failing tests.
- **Test Infrastructure Improvements:**
    - Moved the `tests` directory to the project root, following standard Python project structure.
    - Added a comprehensive Docker-based PostgreSQL testing setup.
    - Resolved numerous linting issues in the test suite.

### Documentation

- **Schema Naming Proposal:** Proposed new, more intuitive naming conventions for Pydantic schemas to improve developer experience.
- **Comprehensive Docstrings:** Added hundreds of docstrings to modules, classes, functions, and methods, significantly improving code documentation and maintainability.
- **README and Onboarding:** Updated the `README.md` and other documentation to reflect new features, testing procedures, and setup instructions.

### Dependency Management

- **Dependabot Configuration:** Added a Dependabot configuration to automate dependency updates.
- **Dependency Updates:** Updated several core dependencies to their latest versions.
- **Unused Dependency Removal:** Removed unused dependencies like `requests` and `bump-pydantic`.
