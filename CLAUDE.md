# Kwik - Claude Code Context

## Project Overview

Kwik is a web framework for building modern, batteries-included, RESTful backends with Python 3.11+. It's based on FastAPI and delivers an opinionated, concise, business-oriented API.

**Key Technologies:**
- FastAPI for web framework
- SQLAlchemy for ORM
- AsyncPG for PostgreSQL async support
- Pydantic for data validation
- Python 3.11+

## Project Structure

```
src/kwik/
├── api/           # FastAPI routes and endpoints
├── core/          # Configuration and security
├── crud/          # Database operations (Create, Read, Update, Delete)
├── database/      # Database connection and session management
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas for API validation
├── utils/         # Utility functions
└── applications/  # Application runners (uvicorn, gunicorn)
```

## Common Commands

### Development
```bash
# Install dependencies (using uv)
uv sync

# Run development server with hot reload
uv run python -m kwik

# Run with specific runner
uv run python -m kwik.applications.uvicorn
uv run python -m kwik.applications.gunicorn
```

### Testing

#### Local Testing Setup
```bash
# Start PostgreSQL test database (required for database tests)
docker compose -f docker-compose.test.yml up -d

# Wait for database to be ready
docker compose -f docker-compose.test.yml exec postgres-test pg_isready -U postgres -d kwik_test

# Run all tests with coverage
uv run pytest

# Run tests with detailed coverage report
uv run pytest --cov=src/kwik --cov-report=term-missing

# Run specific test file
uv run pytest src/tests/test_crud_users.py

# Run specific test method
uv run pytest src/tests/test_crud_users.py::TestUserCRUD::test_create_user

# Run tests in parallel (faster)
uv run pytest -n auto

# Run only unit tests (skip integration tests)
uv run pytest -m "not integration"

# Stop and clean up test database
docker compose -f docker-compose.test.yml down -v
```

#### Test Database
- **PostgreSQL Test Database**: Runs on port 5433 (different from development)
- **Database Name**: kwik_test
- **Credentials**: postgres/root (test-only, safe to use)
- **Docker Compose**: `docker-compose.test.yml`

#### Test Structure
```
src/tests/
├── conftest.py              # Pytest configuration and fixtures
├── utils/                   # Test utilities and factories
│   ├── __init__.py
│   ├── factories.py         # Factory Boy factories for test data
│   └── helpers.py           # Helper functions for tests
├── test_crud_users.py       # CRUD operation tests
├── test_crud_roles.py       # Role CRUD tests
├── test_api_endpoints.py    # API endpoint tests
└── endpoints/
    └── test_docs.py         # Documentation endpoint tests
```

#### Writing Tests
- Use `db_session` fixture for database access
- Use `clean_db` fixture to ensure clean state between tests
- Use factories from `tests.utils` for creating test data
- Mark integration tests with `@pytest.mark.integration`
- Mark slow tests with `@pytest.mark.slow`

#### Continuous Integration
- **GitHub Actions**: Automatically runs tests on PRs and pushes to main/develop
- **Test Workflow**: `.github/workflows/test.yml`
- **Database**: Uses the same Docker Compose setup as local testing
- **Coverage**: Uploads coverage reports to Codecov (if configured)
- **Linting**: Runs ruff checks and formatting validation

### Code Quality
```bash
# Run linter and formatter
uv run ruff check .
uv run ruff format .

# Fix auto-fixable issues
uv run ruff check --fix .
```

## Code Style Guidelines

- **Line length**: 120 characters
- **Python version**: 3.11+
- **Indentation**: 4 spaces
- **Linting**: Ruff with "ALL" rules enabled
- **Type hints**: Use type annotations throughout

## Database

- **ORM**: SQLAlchemy 1.4.x
- **Database**: PostgreSQL (via AsyncPG)
- **Migrations**: Alembic
- **Connection**: Async connection pooling

## API Patterns

- Follow FastAPI conventions for route definitions
- Use Pydantic schemas for request/response validation
- Implement CRUD operations in `crud/` directory
- Database models in `models/`
- API schemas in `schemas/`

## Development Workflow

1. **Setup**: Install dependencies with `uv sync`
2. **Development**: Run `uv run python -m kwik` for hot-reload server
3. **Testing**: Run `uv run pytest` before committing
4. **Linting**: Run `uv run ruff check .` and fix issues
5. **API Documentation**: Available at `http://localhost:8080/docs`

## Repository Context

- **Status**: Pre-release, active development
- **License**: MIT
- **Documentation**: https://kwik.rocks
- **Repository**: https://github.com/dmezzogori/kwik

## Notes for Claude Code

- This is a Python web framework project using FastAPI
- Focus on maintaining consistency with existing patterns
- Pay attention to async/await patterns throughout the codebase
- Database operations should use the established CRUD patterns
- All new endpoints should include proper Pydantic schemas
- Follow the existing project structure when adding new features

## Framework Improvement Analysis

*Analysis Date: 2025-07-29 | Last Updated: 2025-07-30*

### 🔴 **CRITICAL ISSUES (Most Urgent)**

#### 1. **Major Dependency Updates**
- **Priority**: CRITICAL  
- **Issue**: Using severely outdated packages with security implications
- **Critical Updates Needed**:
  - SQLAlchemy: `1.4.48` → `2.0.41` (major version behind)
  - Pydantic: `1.10.2` → `2.11.7` (major version behind)
  - FastAPI: `0.115.0` → `0.116.1` (minor update)
  - Alembic: `1.8.1` → latest stable
- **Risk**: Security vulnerabilities, deprecated APIs, compatibility issues

#### 2. **SQLAlchemy 2.0 Migration**
- **Priority**: CRITICAL
- **Issue**: Using deprecated SQLAlchemy 1.4 patterns throughout codebase
- **Impact**: Deprecation warnings in tests, future compatibility issues
- **Files Affected**: `src/kwik/database/base.py`, all model files, CRUD operations

### 🟠 **HIGH PRIORITY**

#### 3. **Pydantic v2 Migration**
- **Priority**: HIGH  
- **Issue**: Using deprecated Pydantic v1 patterns
- **Files Affected**: 
  - `src/kwik/core/config.py` - Using deprecated `BaseSettings`, `@validator`
  - All schema files using old validation patterns
- **Impact**: Performance improvements, future compatibility

#### 4. **Test Coverage Enhancement**
- **Priority**: HIGH
- **Current**: ~27% coverage (improved from 21% but still low)
- **Missing Coverage**:
  - CSV exporter: 0% coverage
  - AutoRouter: 22% coverage  
  - Utilities: 24-43% coverage
  - WebSocket functionality: 22% coverage

### 🟡 **MEDIUM PRIORITY**

#### 5. **API Functionality Expansion**
- **Priority**: MEDIUM
- **Current State**: Basic CRUD operations only
- **Missing Features**:
  - Bulk operations
  - Advanced filtering/search
  - File upload/download endpoints
  - WebSocket real-time features
  - API versioning strategy
  - Rate limiting
  - Caching mechanisms

#### 6. **Database Layer Improvements**
- **Priority**: MEDIUM
- **Issues**:
  - No connection pooling optimization
  - Missing database migration management
  - No query optimization
  - Limited transaction handling

#### 7. **Error Handling & Logging**
- **Priority**: MEDIUM
- **Issues**:
  - Basic exception handling
  - Limited error response standardization
  - Minimal logging configuration
  - No structured logging for production

### 🟢 **LOW PRIORITY**

#### 8. **Performance Optimizations**
- **Priority**: LOW
- **Opportunities**:
  - Implement async patterns consistently
  - Database query optimization
  - Response caching
  - Connection pool tuning
  - Background task processing

#### 9. **Documentation Improvements**
- **Priority**: LOW (per README: "documentation is not complete yet")
- **Current**: Basic MkDocs setup exists
- **Needs**: API reference, advanced usage examples, deployment guides

#### 10. **Development Experience**
- **Priority**: LOW
- **Improvements**:
  - Better development tooling
  - Docker development setup
  - CI/CD pipeline improvements
  - Code formatting automation

### 🔧 **Quick Commands for Common Issues**
```bash
# Fix auto-fixable linting issues
uv run ruff check --fix .

# Apply unsafe fixes (use carefully)
uv run ruff check --fix --unsafe-fixes

# Update dependencies (after testing)
# Update pyproject.toml manually, then:
uv sync

# Run tests to check current status
uv run pytest --cov=src/kwik --cov-report=term-missing

# Check for security issues
uv run ruff check . | grep S[0-9]
```