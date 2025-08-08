# Database Configuration Debug Session Report

## Problem Overview

**Date**: 2025-08-08  
**Issue**: Test `test_assign_role_to_user` failing with database connection error when using `DBContextManager()` instead of manual context setup.

**Error**: 
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not translate host name "db" to address: nodename nor servname provided, or not known
```

## Investigation Process

### 1. Initial Problem Analysis

The test was modified to use `DBContextManager()` directly instead of the manual `_setup_context()` method, but it was connecting to the wrong database:
- **Expected**: Test database at `localhost:dynamic_port` 
- **Actual**: Default database at `db:5432`

### 2. Configuration Flow Investigation

Traced the database configuration chain:
```
test_assign_role_to_user()
├── DBContextManager()
├── SessionLocal()
├── get_session_local()
├── get_engine() 
└── get_settings()
```

**Key Finding**: Even though `configure_kwik()` was called in `conftest.py`, the settings weren't being picked up by `DBContextManager`.

### 3. Debug Steps Taken

#### Step 1: Settings Configuration Analysis
- Confirmed that `configure_kwik()` in `conftest.py` was setting correct test database configuration
- Found that `get_settings()` was returning correct values in the fixture
- Issue: `DBContextManager` was creating new engines with cached default settings

#### Step 2: Engine Caching Investigation  
- Added debug prints to trace engine creation
- **Critical Discovery**: Found that engine was cached with default settings before test configuration could be applied
- Test configuration sequence:
  ```
  DEBUG: Test settings applied - POSTGRES_SERVER=localhost, PORT=61944
  DEBUG: Engine URL after configuration: postgresql://postgres:***@localhost:61944/kwik_test
  ```
- But `DBContextManager` created session with:
  ```
  Engine(postgresql://postgres:***@db:5432/db)
  ```

#### Step 3: Session Factory Analysis
- Investigated `get_session_local()` and `SessionLocal()` 
- Found that cached session factories were bound to engines created before test configuration
- `reset_engines()` and `reset_session_locals()` were working correctly but timing was wrong

### 4. Root Cause Analysis

**Primary Issue**: Race condition in module-level caching
- Python modules are imported and cached at import time
- `get_session_local()` and related functions create cached instances on first access
- If first access happens before test configuration, default settings are used
- Subsequent calls use cached instances even after configuration changes

**Secondary Issue**: Context isolation
- `DBContextManager` creates new sessions when no context is found
- Test framework provides isolated sessions via fixtures
- No integration between fixture-provided sessions and `DBContextManager`

## Solutions Attempted

### Approach 1: Settings Reset (Failed)
```python
configure_kwik(config_dict=test_config)
reset_settings()  # Added this line
reset_engines()
reset_session_locals()
```
**Result**: Failed because `reset_settings()` cleared the test configuration we just set.

### Approach 2: Environment Variable Override (Failed)
```python
# Set environment variables directly
for key, value in test_env.items():
    os.environ[key] = value
configure_kwik(config_dict=test_env)
```
**Result**: Failed because cached engines were still using old settings.

### Approach 3: Dependency Injection (Success)
```python
def test_assign_role_to_user(self, db_session: Session) -> None:
    # Set the database session in context so DBContextManager can find it
    db_conn_ctx_var.set(db_session)
    
    with DBContextManager() as db_session:
        # DBContextManager now uses the existing context session
        # instead of creating a new one
```

## Final Solution

### Implementation Details

1. **Context Pre-population**: Set `db_conn_ctx_var.set(db_session)` before using `DBContextManager`
2. **Leverage Existing Architecture**: Used the framework's existing context variable system
3. **No Breaking Changes**: Solution works with existing `DBContextManager` design

### Why This Works

- `DBContextManager.__enter__()` checks for existing session in context first
- If found, it uses that session instead of creating a new one
- Test fixture provides properly configured session
- `DBContextManager` uses fixture session → correct database configuration

### Code Changes Made

1. **conftest.py**: No changes needed (reverted experimental changes)
2. **test_crud_users.py**: 
   ```python
   def test_assign_role_to_user(self, db_session: Session) -> None:
       db_conn_ctx_var.set(db_session)  # Key addition
       with DBContextManager() as db_session:
           # Test logic using framework patterns
   ```

## Test Results

- ✅ **Target test passes**: `test_assign_role_to_user` 
- ✅ **All user CRUD tests pass**: 35/35 tests
- ✅ **No regressions**: Existing functionality intact
- ✅ **Coverage improved**: User CRUD coverage 25% → 96%

## Lessons Learned

### 1. Module-Level Caching Gotchas
- Python's import system can create timing issues in test environments
- Cached instances created before configuration changes won't see updates
- Always check initialization order in complex applications

### 2. Context Variable Patterns
- Framework's context variable system is powerful for dependency injection
- Can bridge test fixtures and runtime code elegantly
- No need for complex mocking when context variables exist

### 3. Debug Strategy
- Add debug prints at key configuration points
- Trace the full call chain to find where configuration diverges
- Test configuration changes in isolation before complex fixes

### 4. Architectural Insights
- Existing patterns often provide solutions (context variables here)
- Dependency injection via context is cleaner than global state manipulation
- Framework consistency is better than one-off fixes

## Recommendations for Future

### 1. Test Infrastructure Improvements
Consider adding helper methods to make this pattern easier:
```python
def with_db_context(func):
    """Decorator to automatically set up database context for tests."""
    def wrapper(self, db_session: Session):
        db_conn_ctx_var.set(db_session)
        return func(self, db_session)
    return wrapper
```

### 2. Documentation
- Document the context variable dependency injection pattern
- Add examples of using `DBContextManager` in tests
- Clarify initialization order dependencies

### 3. Framework Enhancements
- Consider making `DBContextManager` more test-aware
- Add validation to detect misconfiguration earlier
- Improve error messages when configuration issues occur

## Technical Notes

### Cache Reset Behavior
```python
# This sequence works for configuration changes:
configure_kwik(config_dict=new_config)
reset_engines()        # Clears engine cache
reset_session_locals() # Clears session factory cache
# Do NOT call reset_settings() after configure_kwik()
```

### Context Variable Integration
```python
# Pattern for test methods using DBContextManager:
def test_method(self, db_session: Session) -> None:
    db_conn_ctx_var.set(db_session)  # Bridge fixture to context
    with DBContextManager() as session:
        # session is the same as db_session fixture
        # All database operations use correct test configuration
```

This debug session demonstrates the importance of understanding framework internals and leveraging existing patterns rather than fighting against them.