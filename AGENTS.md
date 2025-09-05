# Kwik - Claude Code Context

## Project Overview

Kwik is a web framework for building modern, batteries-included, RESTful backends with Python 3.12+. It's based on FastAPI and delivers an opinionated, concise, business-oriented API.

**Key Technologies:**
- Python 3.12+
- FastAPI for web framework
- SQLAlchemy 2.0+ for ORM
- Pydantic for data validation
- PostgreSQL support

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

# Run development server
kwik
```

### Testing

#### Local Testing Setup
```bash
# Run all tests in parallel with coverage (default behavior - fast!)
pytest

# Run tests without parallel execution (for debugging)
pytest -n 0

# Run tests with detailed coverage report  
pytest --cov=src/kwik --cov-report=term-missing

# Run specific test file
pytest tests/crud/test_crud_users.py

# Run specific test method
pytest tests/crud/test_crud_users.py::TestUserCRUD::test_create_user

# Run tests by category (using markers)
pytest -m crud                    # Only CRUD tests
pytest -m unit                    # Only unit tests  
pytest -m integration             # Only integration tests
pytest -m "not slow"              # Skip slow tests (fast feedback)
pytest -m "crud and not slow"     # CRUD tests that aren't slow

# Disable coverage for even faster execution during development
pytest --disable-warnings --tb=short
```

#### Test Database
- **PostgreSQL Test Database**: Automatically managed by testcontainers
- **Database Name**: kwik_test
- **Credentials**: postgres/root (test-only, safe to use)
- **Container Management**: Automatic startup, readiness checks, and cleanup

#### Test Structure
```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── utils/                   # Test utilities and factories
│   ├── __init__.py
│   ├── factories.py         # Factory Boy factories for test data
│   └── helpers.py           # Helper functions for tests
├── test_crud_users.py       # CRUD operation tests
├── test_crud_roles.py       # Role CRUD tests
├── test_api_endpoints.py    # API endpoint tests
```

#### Continuous Integration
- **GitHub Actions**: Automatically runs tests on PRs and pushes to main/develop
- **Test Workflow**: `.github/workflows/test.yml`
- **Database**: Uses testcontainers for automatic PostgreSQL management
- **Coverage**: Uploads coverage reports to Codecov
- **Linting**: Runs ruff checks and formatting validation

### Code Quality & Common Commands
```bash
# Run linter and formatter
ruff check
ruff format

# Fix auto-fixable issues
ruff check --fix

# Apply unsafe fixes (use carefully)
ruff check --fix --unsafe-fixes

# Update dependencies (after testing)
# Update pyproject.toml manually, then:
uv sync

# Run tests to check current status
pytest --cov=src/kwik --cov-report=term-missing
```

### Documentation

#### Local Development
```bash
# Start documentation website locally
cd docs
docker compose up

# Access at http://localhost:8000
```

#### Documentation Hosting & Deployment
- **Technology**: MkDocs Material
- **Source files**: Located in `docs/handbook/` 
- **GitHub Pages**: Hosted at `https://davide.mezzogori.com/kwik/`
- **Auto-deployment**: GitHub Actions workflow `.github/workflows/mkdocs.yml`

#### Documentation Update Workflow
1. Make changes to documentation files in `docs/handbook/`
2. Commit and push to feature branch
3. Merge or push changes to `main` branch (required for deployment)
4. GitHub Actions automatically builds and deploys to `gh-pages` branch
5. Documentation updates live at `https://davide.mezzogori.com/kwik/`

**Note**: Documentation only rebuilds when changes reach the `main` branch, not from feature branches. Manual deployment possible via GitHub Actions `workflow_dispatch`.

## Code Style Guidelines

- **Line length**: 120 characters
- **Python version**: 3.12+
- **Indentation**: 4 spaces
- **Linting**: Ruff with "ALL" rules enabled
- **Type hints**: Use type annotations throughout

## Database

- **ORM**: SQLAlchemy 2.0+
- **Database**: PostgreSQL (via AsyncPG)
- **Migrations**: Alembic
- **Connection**: Async connection pooling

## API Patterns

- Follow FastAPI conventions for route definitions
- Use Pydantic v2 schemas for request/response validation
- Implement CRUD operations in `crud/` directory
- Database models in `models/`
- API schemas in `schemas/`

## Development Workflow

1. **Setup**: Install dependencies with `uv sync`
2. **Development**: Run `kwik` for hot-reload server
3. **Git Workflow**: Use feature branches (`feature/your-feature-name`)
4. **Before starting work**: Run `pytest` to have a reference for existing tests results and coverage
5. **After changes**: Run `pytest` to ensure tests pass
6. **Linting**: Run `ruff check` and fix issues
7. **Format**: Run `ruff format` to apply code style

## Release Workflow

Kwik uses an automated release process with GitHub Actions and PyPI trusted publishing.

### Development Phase
1. Work on feature branches (`feature/feature-name`)
2. Make regular commits with descriptive messages
3. Run tests and linting locally during development

### Release Preparation
1. **Update Version:**
   - Update version in `pyproject.toml` to match the intended release version
   - **CRITICAL**: This must match the tag version (e.g., if tagging `v1.2.0`, set version to `"1.2.0"`)

2. **Update Documentation:**
   - Move `CHANGELOG.md` [Unreleased] content to new versioned section with release date
   - Update `ROADMAP.md` by removing completed tasks (git history preserves them)
   - Document any breaking changes or migration steps

3. **Pre-release Validation:**
   ```bash
   # Run full test suite
   pytest
   
   # Check code quality
   ruff check
   ruff format
   ```

4. **Rebase Feature Branch:**
   ```bash
   # Ensure main branch is up to date
   git checkout main
   git pull origin main
   
   # Rebase feature branch onto main to maintain linear history
   git checkout feature/your-feature-name
   git rebase main
   ```

5. **Commit All Updates:**
   ```bash
   git add pyproject.toml CHANGELOG.md ROADMAP.md
   git commit -m "docs: prepare v1.x.x release"
   ```

### Release Execution
1. **Create Pull Request:**
   ```bash
   gh pr create --title "Release v1.x.x" --body "Release preparation for v1.x.x"
   ```

2. **Merge to Main:**
   - Use GitHub UI to merge PR maintaining linear history (rebase or squash merge)
   - **CRITICAL**: Maintain linear history - no merge commits

3. **Tag and Trigger Release:**
   ```bash
   # Switch to main and pull latest
   git checkout main
   git pull origin main
   
   # Create and push version tag
   git tag v1.x.x
   git push origin v1.x.x
   ```

4. **Automated Publishing:**
   - GitHub Actions workflow `.github/workflows/publish.yml` triggers on tag push
   - Workflow runs tests, linting, formatting checks, builds package
   - Publishes to PyPI using trusted publishing (no manual credentials needed)
   - Monitor workflow execution in GitHub Actions tab

### Post-Release
- Verify package appears on PyPI: https://pypi.org/project/kwik/
- Update any dependent projects or documentation
- Monitor for issues or feedback

### Tools Used
- **`git`**: Version control operations (add, commit, tag, push, pull, checkout)
- **`gh`**: GitHub CLI for pull requests and repository management
- **GitHub Actions**: Automated testing, building, and publishing
- **PyPI Trusted Publishing**: Secure automated package publishing

## Repository Context

- **Status**: Pre-release, active development
- **License**: MIT
- **Documentation**: https://davide.mezzogori.com/kwik/
- **Repository**: https://github.com/dmezzogori/kwik

## Notes for Claude Code

- This is a Python web framework project using FastAPI
- Focus on maintaining consistency with existing patterns
- Pay attention to async/await patterns throughout the codebase
- Database operations should use the established CRUD patterns
- All new endpoints should include proper Pydantic schemas
- Follow the existing project structure when adding new features
- Always run tests to validate changes and that everything works correctly
- Run linting and formatting checks
- Run tests and linting and formatting until everything is green
- You cannot skip any of the steps related to running tests and linting and formatting
- You cannot commit if there are any linting or formatting errors, there are pre-commit hooks in place to enforce this.

## Remaining Planned Migrations

### Critical Dependencies
- **Alembic**: Currently v1.8.1, update to latest stable planned

## Testing Recommendations

- Remember that in pytest you must not use magic numbers or magic constants. this will trigger "ruff check". avoid the use of magic numbers/constants in tests.
