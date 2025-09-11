---
title: Writing Endpoints
description: How to build a new REST endpoint in Kwik
---

This guide shows how to create a new API endpoint in Kwik. We’ll build a complete “Projects” feature end‑to‑end so you can follow along and reuse the pattern for your own modules.

What you’ll learn:
- The `AuthenticatedRouter` pattern used across Kwik
- How to declare routes with request/response schemas
- How to require permissions on endpoints
- How to use Kwik dependencies (session, context, settings, auth, queries)
- How to annotate endpoints and raise framework exceptions cleanly

## Quick Mental Model {#quick-mental-model}

- Router: Group endpoints by feature and enforce authentication globally.
- Dependencies: Small, composable helpers that parse queries, provide the DB session, the current user, the CRUD context, and the app settings.
- Permissions: Declarative access rules enforced via a lightweight dependency.
- Exceptions: Raise simple Kwik exceptions; they map to HTTP responses automatically.


## The Router: AuthenticatedRouter {#router}

Kwik exposes an `AuthenticatedRouter` which adds JWT authentication to every route registered under it. You just pick a `prefix` and all endpoints defined in that router will require a valid access token.

Example (Projects):

```python
from kwik.routers import AuthenticatedRouter

projects_router = AuthenticatedRouter(prefix="/projects")
```

Under the hood, this attaches a token dependency to all routes. If the token is missing or invalid, requests are rejected before hitting your handler.


## Defining Routes with Schemas {#defining-routes}

Endpoints in Kwik use Pydantic v2 schemas for validation and FastAPI’s `response_model` for responses. Keep handlers small and delegate data access to CRUD modules.

Minimal example – a read‑list pattern:

```python
from kwik.dependencies import ListQuery, UserContext
from kwik.schemas import Paginated, ProjectProfile
from kwik.crud import crud_projects

@projects_router.get("/", response_model=Paginated[ProjectProfile])
def read_projects(q: ListQuery, context: UserContext) -> Paginated[ProjectProfile]:
    total, data = crud_projects.get_multi(context=context, **q)
    return {"total": total, "data": data}
```

Notes:
- `ListQuery` merges pagination, sorting, and filters into a single dict.
- `UserContext` carries both the DB session and (when available) the current user.
- Return simple dicts that match the response schema; FastAPI validates/serializes.


## Requiring Permissions {#permissions}

Kwik adds a tiny permission checker you can attach to any route. You pass one or more permission names; if the current user doesn’t have them, the request is denied.

```python
from kwik.core.enum import Permissions
from kwik.dependencies import has_permission

@projects_router.get(
    "/",
    response_model=Paginated[ProjectProfile],
    dependencies=(has_permission(Permissions.projects_management_read),),
)
def read_projects(q: ListQuery, context: UserContext) -> Paginated[ProjectProfile]:
    ...
```

Multiple permissions can be checked at once:

```python
@projects_router.post(
    "/{project_id}/archive",
    dependencies=(has_permission(Permissions.projects_management_update, Permissions.projects_management_read),),
)
def archive_project(...):
    ...
```

## Defining New Permissions {#defining-new-permissions}

System permission names live in `src/kwik/core/enum.py` as the `Permissions` enum. For Projects, you might add:

```python
class Permissions(StrEnum):
    # ...existing entries
    projects_management_create = "projects_management_create"
    projects_management_read = "projects_management_read"
    projects_management_update = "projects_management_update"
    projects_management_delete = "projects_management_delete"
```

Ensure your seeds/migrations create these permissions so roles can grant them.


## Kwik Dependencies (what to inject and when) {#dependencies}

All reusable route dependencies live in `kwik.dependencies`. Use these building blocks to keep handlers small and consistent.

### Settings

Injects the current `BaseKwikSettings` instance configured for the app (`src/kwik/dependencies/settings.py`). Use it for anything that depends on configuration (e.g., tokens).

Example:

```python
from kwik.dependencies import Settings

def handler(settings: Settings) -> None:  # access env‑driven config safely
    ...
```

### Session

Provides a per‑request SQLAlchemy session with automatic commit/close (`src/kwik/dependencies/session.py`). Prefer using `UserContext`/`NoUserContext` instead of `Session` directly in handlers.

### Context (UserContext / NoUserContext)

Bundles the DB session and (for `UserContext`) the authenticated user (`src/kwik/dependencies/context.py`). Pass this to CRUD functions to keep data access uniform.

Example:

```python
from kwik.dependencies import UserContext

def handler(context: UserContext) -> None:
    ...
```

### Authentication (current_user / current_token)

`current_user` gives you the authenticated `User` model; `current_token` exposes the decoded JWT payload (`src/kwik/dependencies/users.py`, `src/kwik/dependencies/token.py`).

Use `user: current_user` when you need ownership/auditing in the handler body.

### Permission guard

`has_permission(...)` is a decorator‑style dependency to enforce permissions at the route level (`src/kwik/dependencies/permissions.py`).

Example:

```python
from kwik.core.enum import Permissions
from kwik.dependencies import has_permission

dependencies=(has_permission(Permissions.projects_management_read),)
```

### ListQuery (pagination, sorting, filters)

`ListQuery` combines pagination, sorting, and filters into a single input dict (`src/kwik/dependencies/list_query.py`).

- Pagination: `skip`, `limit`
- Sorting: `?sorting=id:desc,created_at` → `[('id', 'desc'), ('created_at', 'asc')]`
- Filters: key/value pair, e.g. `?filter_key=name&value=alpha`


## Why `context` matters (CRUD boundary) {#context}

The `context` dependency is the bridge between your route and the data layer. It centralizes:
- The active SQLAlchemy session
- The current user (for auditing/ownership checks)

By always calling CRUD functions with `context=...`, your endpoints stay small and consistent, and all DB/session/user concerns remain in one place.


## Why `settings` matters (security/config) {#settings}

Many security utilities depend on application configuration (e.g., `SECRET_KEY`, token expiration). Inject `settings: Settings` whenever you need to:
- Create or validate JWTs
- Access environment‑driven configuration (ports, DB, debug flags, etc.)

You should not instantiate settings manually inside handlers—always inject with the dependency so the same instance is used across the app.


## Annotating Endpoints Cleanly {#annotations}

Follow these conventions to keep handlers clear and type‑safe:
- Use explicit input schemas (e.g., `ProjectDefinition`, `ProjectUpdate`) and annotate return types with your response model types.
- Always pass `context: UserContext` (or `NoUserContext`) to CRUD functions.
- Use `current_user` when you need the user model (e.g., for ownership).

Example – update a project:

```python
from kwik.dependencies import UserContext
from kwik.schemas import ProjectProfile, ProjectUpdate
from kwik.crud import crud_projects

@projects_router.put("/{project_id}", response_model=ProjectProfile)
def update_project(project_id: int, project_in: ProjectUpdate, context: UserContext) -> Project:
    return crud_projects.update(entity_id=project_id, obj_in=project_in, context=context)
```


## Raising Exceptions the Kwik Way {#exceptions}

Raise the lightweight Kwik exceptions instead of FastAPI’s `HTTPException`. They’re converted into proper JSON responses by the global exception handler.

Common ones:
- `DuplicatedEntityError` → 409 Conflict
- `AccessDeniedError` → 403 Forbidden
- `EntityNotFoundError` → 404 Not Found
- `AuthenticationFailedError` → 401 Unauthorized
- `InactiveUserError` → 400 Bad Request
- `TokenValidationError` → 400 Bad Request (invalid token)

Example – conflict on creation:

```python
from kwik.exceptions import DuplicatedEntityError

@projects_router.post("/", response_model=ProjectProfile)
def create_project(project_in: ProjectDefinition, context: UserContext) -> Project:
    existing = crud_projects.get_by_name(name=project_in.name, context=context)
    if existing is not None:
        raise DuplicatedEntityError
    return crud_projects.create(obj_in=project_in, context=context)
```


## Complete Walkthrough: Projects {#example-projects}

Below is a complete “Projects” walkthrough you can adapt in your app. It shows permissions, schemas, CRUD signatures, and the router.

```python
from kwik.core.enum import Permissions
from kwik.crud import crud_projects
from kwik.dependencies import ListQuery, UserContext, has_permission
from kwik.exceptions import DuplicatedEntityError
from kwik.routers import AuthenticatedRouter
from kwik.schemas import Paginated, ProjectProfile, ProjectDefinition, ProjectUpdate

projects_router = AuthenticatedRouter(prefix="/projects")

@projects_router.get(
    "/",
    response_model=Paginated[ProjectProfile],
    dependencies=(has_permission(Permissions.projects_management_read),),
)
def read_projects(q: ListQuery, context: UserContext) -> Paginated[ProjectProfile]:
    total, data = crud_projects.get_multi(context=context, **q)
    return {"total": total, "data": data}

@projects_router.post(
    "/",
    response_model=ProjectProfile,
    dependencies=(has_permission(Permissions.projects_management_create),),
)
def create_project(project_in: ProjectDefinition, context: UserContext) -> Project:
    existing = crud_projects.get_by_name(name=project_in.name, context=context)
    if existing is not None:
        raise DuplicatedEntityError
    return crud_projects.create(obj_in=project_in, context=context)

@projects_router.get(
    "/{project_id}",
    response_model=ProjectProfile,
    dependencies=(has_permission(Permissions.projects_management_read),),
)
def read_project(project_id: int, context: UserContext) -> Project:
    return crud_projects.get_if_exist(entity_id=project_id, context=context)

@projects_router.put(
    "/{project_id}",
    response_model=ProjectProfile,
    dependencies=(has_permission(Permissions.projects_management_update),),
)
def update_project(project_id: int, project_in: ProjectUpdate, context: UserContext) -> Project:
    return crud_projects.update(entity_id=project_id, obj_in=project_in, context=context)
 @projects_router.delete(
     "/{project_id}",
     response_model=ProjectProfile,
     dependencies=(has_permission(Permissions.projects_management_delete),),
 )
 def delete_project(project_id: int, context: UserContext) -> Project:
     return crud_projects.delete(entity_id=project_id, context=context)
```

What you’d have around it:

- Schemas (in `src/kwik/schemas/project.py`):

  ```python
  from pydantic import BaseModel

  class ProjectDefinition(BaseModel):
      name: str
      description: str | None = None

  class ProjectUpdate(BaseModel):
      name: str | None = None
      description: str | None = None

  class ProjectProfile(BaseModel):
      id: int
      name: str
      description: str | None = None
  ```

- CRUD interface (in `src/kwik/crud/projects.py`):

  ```python
  from kwik.crud.context import Context

  def get_multi(*, context: Context, skip: int = 0, limit: int = 100, sort: list[tuple[str, str]] | None = None, **filters):
      ...  # return (total, [Project])

  def get_by_name(*, name: str, context: Context):
      ...  # return Project | None

  def create(*, obj_in: ProjectDefinition, context: Context):
      ...  # return Project

  def get_if_exist(*, entity_id: int, context: Context):
      ...  # return Project (or raise EntityNotFoundError internally)

  def update(*, entity_id: int, obj_in: ProjectUpdate, context: Context):
      ...  # return Project

  def delete(*, entity_id: int, context: Context):
      ...  # return Project
  ```

!!! tip "Use dependencies consistently"
    - Always pass `context` to CRUD functions.
    - Use `ListQuery` for collections, so pagination/sorting/filters stay uniform.
    - Inject `Settings` when you need application configuration.


## Wire It Into the API {#wiring}

After defining your router (e.g., `projects_router`), include it in the main API router in `src/kwik/api/api.py`:

```python
from .endpoints import projects_router

api_router.include_router(projects_router)
```

That’s it — you now have a fully authenticated, permission‑aware, typed endpoint that plays nicely with Kwik’s patterns.
