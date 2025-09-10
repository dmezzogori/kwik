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
├── dependencies/  # Dependency injection and management
├── exceptions/    # Custom exceptions and error handling
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic schemas for API validation
├── testing/       # Testing utilities and fixtures
├── utils/         # Utility functions
├── applications/  # Application runners (uvicorn, gunicorn)
├── database.py    # Database connection and session management
├── logging.py     # Logging configuration
├── routers.py     # API route class definitions
├── security.py    # Security utilities and authentication
└── settings.py    # Application settings and configuration
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
uv run pytest

# Run tests without parallel execution (for debugging)
uv run pytest -n 0

# Run tests with detailed coverage report  
uv run pytest --cov=src/kwik --cov-report=term-missing

# Run specific test file
uv run pytest tests/crud/test_crud_users.py

# Run specific test method
uv run pytest tests/crud/test_crud_users.py::TestUserCRUD::test_create_user

# Disable coverage for even faster execution during development
uv run pytest --disable-warnings --tb=short
```

#### Test Database
- **PostgreSQL Test Database**: Automatically managed by testcontainers
- **Database Name**: kwik_test
- **Credentials**: postgres/root (test-only, safe to use)
- **Container Management**: Automatic startup, readiness checks, and cleanup

#### Test Structure
```
tests/
├── conftest.py                          # Pytest configuration and fixtures
├── api/                                 # API endpoint tests
│   ├── conftest.py                      # API-specific fixtures
│   ├── test_login_router.py            # Authentication endpoint tests
│   ├── test_permissions_router.py      # Permissions API tests
│   ├── test_roles_router.py            # Roles API tests
│   └── test_users_router.py            # Users API tests
├── applications/                        # Application runner tests
│   └── test_kwik.py                     # Main application tests
├── crud/                                # CRUD operation tests
│   ├── test_autocrud_validation.py     # AutoCRUD validation tests
│   ├── test_crud_permissions.py        # Permission CRUD tests
│   ├── test_crud_roles.py              # Role CRUD tests
│   └── test_crud_users.py              # User CRUD tests
├── dependencies/                        # Dependency injection tests
│   ├── test_filter_query.py            # Filter query dependency tests
│   ├── test_session.py                 # Database session dependency tests
│   └── test_sorting_query.py           # Sorting query dependency tests
├── security/                            # Security module tests
│   └── test_security.py                # Security utilities tests
├── testing/                             # Testing framework tests
│   ├── conftest.py                      # Testing-specific fixtures
│   ├── test_client_auth.py             # Test client authentication tests
│   ├── test_client.py                  # Test client tests
│   ├── test_factories.py               # Test factory tests
│   └── test_scenario.py                # Test scenario tests
└── utils/                               # Test utilities
    ├── helpers.py                       # Helper functions for tests
    └── test_files.py                    # File utility tests
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
uv run ruff check
uv run ruff format

# Fix auto-fixable issues
uv run ruff check --fix

# Apply unsafe fixes (use carefully)
uv run ruff check --fix --unsafe-fixes

# Update dependencies (after testing)
# Update pyproject.toml manually, then:
uv sync

# Run tests to check current status
uv run pytest
```

### Documentation

#### Local Development
```bash
# Start documentation website locally
cd docs
docker compose up

# Access at http://localhost:8000 using curl or playwright MCP
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
4. **Before starting work**: Run `uv run pytest` to have a reference for existing tests results and coverage
5. **After changes**: Run `uv run pytest` to ensure tests pass
6. **Linting**: Run `uv run ruff check` and fix issues
7. **Format**: Run `uv run ruff format` to apply code style

## Release Workflow

Kwik uses an automated release process with GitHub Actions, PyPI trusted publishing, and Linear project management integration.

### Pre-Release Planning (Linear)
1. **Feature Development**: Work on feature branches with Linear issue tracking
2. **Issue Management**: Update Linear issues to "Done" status when features are complete
3. **Project Updates**: Post project updates in Linear celebrating milestone completion

### Release Preparation
1. **Update Version FIRST:**
   - **CRITICAL**: Update version in `pyproject.toml` to match the intended release version BEFORE creating any PR
   - This must match the tag version (e.g., if tagging `v1.3.0`, set version to `"1.3.0"`)
   - Version update must be committed before proceeding
   - You MUST run `uv sync` after updating the version to ensure lock file is updated

2. **Update Documentation:**
   - Move `CHANGELOG.md` [Unreleased] content to new versioned section with release date
   - Add comprehensive release notes with features, improvements, and technical details
   - Document any breaking changes or migration steps
   - Update any roadmap references (if using markdown roadmaps)

3. **Pre-release Validation:**
   ```bash
   # Run full test suite
   uv run pytest
   
   # Check code quality
   uv run ruff check
   uv run ruff format
   ```

4. **Commit Release Preparation:**
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "docs: prepare vX.X.X release" -S
   ```

### Release Execution
1. **Create PR from Feature Branch:**
   ```bash
   # Push feature branch with release preparation commits
   git push -u origin feature/your-feature-name
   
   # Create PR with comprehensive release information
   gh pr create --title "Release vX.X.X" --body "Comprehensive release description..."
   ```

2. **Manual Rebase Merge (Required for Signed Commits):**
   - **IMPORTANT**: `gh pr merge --rebase` fails with signed commit repositories
   - **Manual Process Required:**
   ```bash
   # Manual rebase merge to maintain signed commits
   git checkout main
   git pull origin main
   git rebase origin/feature/your-feature-name
   git push origin main
   ```
   - GitHub will automatically detect and close the PR

3. **Tag and Trigger Release:**
   ```bash
   # Create and push version tag to trigger automated publishing
   git tag vX.X.X
   git push origin vX.X.X
   ```

4. **Automated Publishing:**
   - GitHub Actions workflow `.github/workflows/publish.yml` triggers on tag push
   - Workflow runs tests, linting, formatting checks, builds package
   - Publishes to PyPI using trusted publishing (no manual credentials needed)
   - Monitor workflow execution in GitHub Actions tab

### Post-Release (Linear Integration)
1. **Verify Publishing:**
   - Confirm package appears on PyPI: https://pypi.org/project/kwik/
   - Check GitHub Actions workflow completed successfully

2. **Update Linear Project Management:**
   - Update main Linear project description with release celebration
   - Mark completed features/epics with release version and PyPI links
   - Post project update announcing successful release
   - Plan next roadmap milestone (move next epic to "Planning" status)

3. **Communication:**
   - Update any dependent projects or documentation
   - Monitor for issues or feedback
   - Share release announcement with team/community

### Critical Notes for Signed Commit Repositories
- **Cannot use `gh pr merge --rebase`** due to GitHub's inability to automatically sign rebase merges
- **Must perform manual rebase merge** to maintain signed commit history
- **Repository rules** may prevent direct pushes to main, requiring PR workflow
- **All commits must be signed** throughout the process

### Tools Used
- **`git`**: Version control operations (add, commit, tag, push, pull, checkout, rebase)
- **`gh`**: GitHub CLI for pull requests and repository management
- **GitHub Actions**: Automated testing, building, and publishing
- **PyPI Trusted Publishing**: Secure automated package publishing
- **Linear**: Project management, issue tracking, and progress updates

## Linear Project Management Integration

### Project Structure
- **Main Project**: "Kwik Framework Development" - https://linear.app/akirasakurai/project/kwik-framework-development-18329547cdb2
- **Epic Issues**: Major features tracked as epics with detailed acceptance criteria
- **Dependencies**: Cross-feature dependencies mapped between epics
- **Milestones**: Key deliverables within projects tracked with milestones

### GitHub Integration
- **Auto-Updates**: Linear issues automatically update status based on PR lifecycle
- **PR Linking**: Use "Resolves AKI-X" in PR descriptions to link Linear issues
- **Status Flow**: In Progress → In Review (PR created) → Done (PR merged)
- **Branch Naming**: Auto-generated branch names for seamless development workflow

### Workflow Integration Best Practices
1. **Feature Development**: Start with Linear issue, create feature branch
2. **Development**: Regular commits with descriptive messages, link to Linear issue
3. **PR Creation**: Always reference Linear issue in PR description with "Resolves AKI-X"
4. **Completion**: Linear automatically updates issue status, celebrate in project updates
5. **Release**: Update Linear project with release information and plan next milestone

### Project Communication
- **Project Updates**: Use Linear's project update feature for milestone announcements
- **Progress Tracking**: Visual progress tracking with dependencies and timelines
- **Team Coordination**: Shared visibility into development progress and priorities

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
