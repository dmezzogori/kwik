# Kwik - Claude Code Context

## Project Overview

Kwik is a web framework for building modern, batteries-included, RESTful backends with Python 3.10+. It's based on FastAPI and delivers an opinionated, concise, business-oriented API.

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
```bash
# Run tests with coverage
uv run pytest

# Run tests with coverage report
uv run pytest --cov=src/kwik --cov-report=term-missing

# Run specific test
uv run pytest src/tests/endpoints/test_docs.py
```

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

*Analysis Date: 2025-07-29*

### 🔴 **CRITICAL ISSUES (Most Urgent)**

#### 1. **Fix Failing Tests** 
- **Priority**: CRITICAL
- **Impact**: Blocking development workflow
- **Issue**: 4 out of 5 tests are failing with 404 errors
- **Location**: `src/tests/endpoints/test_tests.py`
- **Action**: Tests reference `/api/v1/tests/*` endpoints that don't exist in the codebase

#### 2. **Major Dependency Updates**
- **Priority**: CRITICAL  
- **Issue**: Using severely outdated packages with security implications
- **Critical Updates Needed**:
  - SQLAlchemy: `1.4.48` → `2.0.41` (major version behind)
  - Pydantic: `1.10.2` → `2.11.7` (major version behind)
  - FastAPI: `0.115.0` → `0.116.1` (minor update)
  - Alembic: `1.8.1` → latest stable
- **Risk**: Security vulnerabilities, deprecated APIs, compatibility issues

#### 3. **SQLAlchemy 2.0 Migration**
- **Priority**: CRITICAL
- **Issue**: Using deprecated SQLAlchemy 1.4 patterns throughout codebase
- **Impact**: Deprecation warnings in tests, future compatibility issues
- **Files Affected**: `src/kwik/database/base.py`, all model files, CRUD operations

### 🟠 **HIGH PRIORITY**

#### 4. **Code Quality Crisis - 1139 Linting Errors**
- **Priority**: HIGH
- **Issue**: Massive number of linting violations
- **Main Categories**:
  - Missing docstrings (D103, D100)
  - Import organization (I001, E402)
  - Unused imports (F401)
  - Security issues (S311, S101)
  - Style violations (D200, D212)

#### 5. **Pydantic v2 Migration**
- **Priority**: HIGH  
- **Issue**: Using deprecated Pydantic v1 patterns
- **Files Affected**: 
  - `src/kwik/core/config.py` - Using deprecated `BaseSettings`, `@validator`
  - All schema files using old validation patterns
- **Impact**: Performance improvements, future compatibility

#### 6. **Security Improvements**
- **Priority**: HIGH
- **Issues Found**:
  - Using `datetime.utcnow()` (deprecated in Python 3.12+)
  - Weak random generation in tests (`random.choice`)
  - Default credentials in config (`admin@example.com`/`admin`)
  - Token handling could be improved

#### 7. **Test Coverage Enhancement**
- **Priority**: HIGH
- **Current**: 57% coverage (very low for a framework)
- **Missing Coverage**:
  - CSV exporter: 0% coverage
  - AutoRouter: 22% coverage  
  - Utilities: 24-43% coverage
  - WebSocket functionality: 22% coverage

### 🟡 **MEDIUM PRIORITY**

#### 8. **API Functionality Expansion**
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

#### 9. **Database Layer Improvements**
- **Priority**: MEDIUM
- **Issues**:
  - No connection pooling optimization
  - Missing database migration management
  - No query optimization
  - Limited transaction handling

#### 10. **Error Handling & Logging**
- **Priority**: MEDIUM
- **Issues**:
  - Basic exception handling
  - Limited error response standardization
  - Minimal logging configuration
  - No structured logging for production

### 🟢 **LOW PRIORITY**

#### 11. **Performance Optimizations**
- **Priority**: LOW
- **Opportunities**:
  - Implement async patterns consistently
  - Database query optimization
  - Response caching
  - Connection pool tuning
  - Background task processing

#### 12. **Documentation Improvements**
- **Priority**: LOW (per README: "documentation is not complete yet")
- **Current**: Basic MkDocs setup exists
- **Needs**: API reference, advanced usage examples, deployment guides

#### 13. **Development Experience**
- **Priority**: LOW
- **Improvements**:
  - Better development tooling
  - Docker development setup
  - CI/CD pipeline improvements
  - Code formatting automation

### 📊 **Summary Statistics**
- **Code Quality**: 1139 linting errors
- **Test Coverage**: 57% (target should be >90%)
- **Failed Tests**: 4 out of 5 tests failing
- **Dependency Age**: Major dependencies 1-2 major versions behind
- **Security**: Multiple deprecated API usages

### 🎯 **Recommended Action Plan**
1. **Week 1**: Fix failing tests, update critical dependencies
2. **Week 2**: SQLAlchemy 2.0 migration, Pydantic v2 migration  
3. **Week 3**: Address critical linting errors (aim for <100 total)
4. **Week 4**: Improve test coverage to >80%
5. **Month 2**: API functionality expansion and security hardening

### 🔧 **Quick Commands for Common Issues**
```bash
# Fix auto-fixable linting issues
uv run ruff check --fix .

# Update dependencies (after testing)
# Update pyproject.toml manually, then:
uv sync

# Run tests to check current status
uv run pytest --cov=src/kwik --cov-report=term-missing

# Check for security issues
uv run ruff check . | grep S[0-9]
```