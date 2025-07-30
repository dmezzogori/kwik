---
mode: agent
model: Claude Sonnet 4
tools: ['changes', 'codebase', 'editFiles', 'fetch', 'findTestFiles', 'runCommands', 'runTests', 'search', 'testFailure', 'usages', 'context7', 'configurePythonEnvironment', 'getPythonEnvironmentInfo', 'getPythonExecutableCommand', 'installPythonPackage']
description: 'Fix specific ruff linting errors in the Kwik codebase by manually addressing issues that cannot be auto-fixed.'
---

# Ruff Code Quality Fixer

Fix specific ruff linting errors in the Kwik codebase that require manual intervention. This prompt is designed to handle errors that cannot be fixed with `--fix` or `--unsafe-fixes` options.

## Target Error Codes
Focus on these specific ruff error codes: **${input:errorCodes:Enter error code(s) (e.g., "F401" or "F401,E402,W292")}**

### Common FastAPI/Pydantic Error Codes
- **F401**: Unused imports (be careful with FastAPI runtime requirements)
- **F811**: Redefined unused name (common with model/schema naming)
- **B008**: Do not perform function calls in argument defaults (FastAPI dependencies)
- **E501**: Line too long (FastAPI route definitions can be verbose)
- **UP**: pyupgrade rules (Python 3.10+ syntax improvements)
- **ANN**: Missing type annotations (critical for FastAPI/Pydantic)
- **SIM**: Code simplification (improve readability)
- **TCH**: Type checking imports (proper TYPE_CHECKING usage)
- **RUF**: Ruff-specific rules (various quality improvements)

## Instructions

1. **Analyze Ruff Errors**: Execute `uv run ruff check --select ${input:errorCodes}` to identify all errors for the specified codes
   - Parse the output to understand the specific issues that need manual fixes
   - Focus only on errors that cannot be automatically fixed
   - Document the total number of errors found and their locations

2. **Manual Code Fixes**: Address each error requiring manual intervention with careful consideration for:
   - **FastAPI Integration**: Ensure imports needed for dependency injection and route generation remain at runtime
   - **Pydantic V1 Patterns**: Use correct `@validator` and `@root_validator` patterns for Pydantic V1
   - **TYPE_CHECKING imports**: Carefully separate runtime imports from type-only imports, considering FastAPI's needs
   - **Model Validation**: Ensure validator methods use `cls` parameter and proper V1 syntax
   - **Function signatures**: Fix parameter types, return types, and missing annotations
   - **Import organization**: Resolve unused imports, missing imports, and import ordering
   - **Code style**: Fix formatting, naming conventions, and structural issues
   - **Error handling**: Improve exception handling and error messages

3. **Test Auto-fixes First**: Before manual intervention, try auto-fixes to reduce manual work
   - Run `uv run ruff check --select ${input:errorCodes} --fix` 
   - Run `uv run ruff check --select ${input:errorCodes} --unsafe-fixes` if safe to do so
   - Only proceed with manual fixes for remaining errors

4. **Verify Library Functionality**: 
   - Test that `uv run python -c "import kwik; print('✅ Library imports successfully')"` works correctly
   - Test that `uv run python -c "import kwik; app = kwik.Kwik(kwik.api.api.api_router); print('✅ Kwik app created successfully')"` creates an app successfully
   - Run at least the docs test: `uv run pytest src/tests/endpoints/test_docs.py -v`
   - If any issues are found, fix them before proceeding

5. **Update Documentation**:
   - Update `CLAUDE.md` in the "Framework Improvement Analysis" section
   - Add a new completed section documenting:
     - Error codes targeted (${input:errorCodes})
     - Number of errors fixed (auto-fixes + manual fixes)
     - Files modified
     - Types of manual interventions required
     - Impact on code quality
   - Update the summary statistics with new error counts
   - Update the action plan to reflect completed work

6. **Commit Changes**:
   - Commit with descriptive message including:
     - Number of errors fixed (e.g., "Fixed 15 ${input:errorCodes} ruff errors")
     - Error codes addressed
     - Brief description of main fixes applied (auto vs manual)
     - Verification that library still works

## Common Manual Fix Patterns for FastAPI and Pydantic

### Pydantic V1 Validators (Current Pattern)
- Use `@validator` for field validation in Pydantic V1
- Ensure class methods use `cls` parameter: `@validator('field_name') def validate_field(cls, v):`
- Use `@root_validator` for model-level validation
- Specify `pre=True` for pre-validation if needed: `@validator('field_name', pre=True)`
- Use `values` parameter in `@root_validator` to access other field values: `@root_validator def validate_model(cls, values):`

### FastAPI Type Import Management
- Move type-only imports to `if TYPE_CHECKING:` blocks to avoid circular imports
- Keep runtime imports outside TYPE_CHECKING when FastAPI needs them for route generation
- **CRITICAL**: FastAPI requires actual imports for dependency injection, response models, and route parameter types
- Be cautious with forward references in FastAPI route signatures - use string literals when necessary
- Import order: stdlib, third-party (FastAPI, Pydantic), local imports

### Pydantic Model Patterns
- Use `BaseModel` from `pydantic` for all data models
- Prefer `from __future__ import annotations` for cleaner forward references
- Use `Field(...)` from pydantic for field validation and metadata
- For model configuration, use `Config` class in Pydantic V1: `class Config: str_strip_whitespace = True`
- Use proper type hints: `str | None` instead of `Optional[str]` (Python 3.10+)

### FastAPI Dependency and Route Annotations
- Keep dependency function type hints as runtime imports (not in TYPE_CHECKING)
- Response model classes must be available at runtime for OpenAPI generation
- Use `Annotated[Type, Depends(...)]` pattern for dependency injection
- Request/response models should inherit from `BaseModel` and be importable

### Type Annotations and Forward References
- Use string literals for forward references: `'ModelName'` instead of bare ModelName
- Call `model_rebuild()` after all models are defined if using forward references
- Add missing return type annotations for all functions and methods
- Use proper generic types: `list[str]` instead of `List[str]` (Python 3.9+)

### Code Style and Structure
- Fix line length violations (120 chars) by restructuring code
- Resolve naming convention violations (snake_case for functions/variables, PascalCase for classes)
- Address indentation and formatting issues
- Use proper docstring formats for API documentation generation

## FastAPI-Specific Considerations

### Critical Runtime Import Requirements
- **Dependencies**: FastAPI dependency functions must have their types available at runtime
- **Response Models**: Classes used in `response_model` parameter must be importable during route definition
- **Request Bodies**: Pydantic models used as request body parameters need runtime availability
- **Path/Query Parameters**: Custom types and validators need to be accessible during route parsing

### Safe TYPE_CHECKING Patterns
```python
from __future__ import annotations

from typing import TYPE_CHECKING
from pydantic import BaseModel
from fastapi import FastAPI, Depends

# Safe for TYPE_CHECKING - used only for type hints
if TYPE_CHECKING:
    from .some_module import SomeTypeForAnnotation

# Must remain at runtime - used by FastAPI
class RequestModel(BaseModel):
    field: str

class ResponseModel(BaseModel):
    result: str

def dependency_function() -> str:
    return "dependency_value"

app = FastAPI()

@app.post("/endpoint", response_model=ResponseModel)  # Needs ResponseModel at runtime
async def endpoint(
    request: RequestModel,  # Needs RequestModel at runtime
    dep: str = Depends(dependency_function),  # Needs dependency_function at runtime
) -> ResponseModel:  # Can use string literal if needed: -> "ResponseModel"
    return ResponseModel(result="success")
```

### Pydantic V1 Current Patterns (In Use)
```python
# CURRENT V1 Pattern (in use in this codebase)
from pydantic import BaseModel, validator, root_validator

class CurrentModel(BaseModel):
    field: str
    
    @validator('field')
    def validate_field(cls, v):  # Use 'cls' not 'self'
        return v.upper()
    
    @root_validator
    def validate_model(cls, values):
        return values
    
    class Config:
        str_strip_whitespace = True
```

## Quality Checks

Before committing, ensure:
- [ ] Library imports successfully: `uv run python -c "import kwik; print('✅ Library imports successfully')"`
- [ ] App creation works: `uv run python -c "import kwik; app = kwik.Kwik(kwik.api.api.api_router); print('✅ Kwik app created successfully')"`
- [ ] FastAPI routes are properly defined and accessible
- [ ] Pydantic models validate correctly with test data
- [ ] At least one test passes to verify functionality: `uv run pytest src/tests/endpoints/test_docs.py -v`
- [ ] No new runtime errors introduced
- [ ] All targeted error codes (${input:errorCodes}) are resolved
- [ ] Import organization follows FastAPI/Pydantic best practices
- [ ] Documentation updated with accurate statistics
- [ ] Commit message is descriptive and informative

### FastAPI-Specific Validation
- [ ] OpenAPI schema generation works: Check `/docs` endpoint functionality
- [ ] Dependency injection works correctly after import changes
- [ ] Request/response model validation functions properly
- [ ] No circular imports that break FastAPI startup
