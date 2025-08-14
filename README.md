# Kwik

<div align="center">
<img src="docs/handbook/docs/img/logo.png" alt="Kwik Logo" width="400">
</div>

---

**Documentation**: https://davide.mezzogori.com/kwik/

**Repository**: https://github.com/dmezzogori/kwik

[![codecov](https://codecov.io/github/dmezzogori/kwik/branch/main/graph/badge.svg?token=7WBOPGCSWS)](https://codecov.io/github/dmezzogori/kwik)
---

Kwik is a web framework for building modern, batteries-included, REST APIs backends with Python 3.12+.
Kwik is based on FastAPI, builds upon it and delivers an opinionated, concise, and business-oriented API.


## Key Features

### 🛠️ Advanced Settings Management

Multi-source configuration system supporting environment variables, files, and programmatic configuration with automatic validation.

```python
from kwik import Kwik, api_router
from kwik.settings import BaseKwikSettings

class MyAppSettings(BaseKwikSettings):
    CUSTOM_API_KEY: str = "default-key"
    MAX_WORKERS: int = 4
    PROJECT_NAME: str = "My Custom API"

# Create settings instance (loads from environment/config files)
settings = MyAppSettings()

# Create Kwik application
app = Kwik(settings=settings, api_router=api_router)
```

### 🚀 AutoCRUD System

Generic CRUD operations with automatic type inference, built-in pagination, filtering, and sorting.

```python
from kwik.crud.autocrud import AutoCRUD
from kwik.crud.context import MaybeUserCtx
from kwik import models, schemas

class ProductCRUD(AutoCRUD[MaybeUserCtx, models.Product, schemas.ProductCreate, schemas.ProductUpdate, int]):
    pass

product_crud = ProductCRUD()

# Automatic pagination and sorting
# In a real Kwik endpoint, `context` is automatically injected using the `UserContext` or `NoUserContext`
total, products = product_crud.get_multi(
    skip=0, limit=10, 
    sort=[("name", "asc"), ("created_at", "desc")],
    context=context,
    category="electronics"
)
```

### 📊 SQLAlchemy Mixins

Pre-built mixins for common database patterns with automatic configuration.

```python
from kwik.models import RecordInfoMixin
from kwik.models import Base
from sqlalchemy import Column, String

class Product(Base, RecordInfoMixin):
    __tablename__ = "products"
    name = Column(String, nullable=False)
    # Automatically includes:
    # - creation_time, last_modification_time (TimeStampsMixin)
    # - creator_user_id, last_modifier_user_id (UserMixin)
```

### 🔐 Built-in RBAC System

Role-based access control with comprehensive permission management.

```python
from kwik.crud import crud_users
from kwik.crud import crud_roles

# Check permissions (requires user object)
if crud_users.has_permissions(user=user, permissions=["product.create", "product.update"]):
    # User has required permissions
    ...

# Assign roles (done through roles CRUD)
crud_roles.assign_user(role=admin_role, user=user, context=context)

# Get all user permissions
permissions = crud_users.get_permissions(user=user)
```

### 📄 Pagination & Sorting Utilities

Ready-to-use pagination schemas and sorting dependencies for clean API endpoints.

```python
from fastapi import APIRouter, Depends
from kwik.schemas import Paginated
from kwik.dependencies import SortingQuery
from kwik.dependencies import UserContext, NoUserContext

router = APIRouter()

@router.get("/products", response_model=Paginated[ProductResponse])
def get_products(
    skip: int = 0, 
    limit: int = 10, 
    sort: SortingQuery = None,
    context = UserContext  # Context dependency injection
):
    total, products = product_crud.get_multi(
        skip=skip, limit=limit, sort=sort, context=context
    )
    return {"total": total, "data": products}

# API usage: GET /products?sort=name:asc,created_at:desc
```

## Acknowledgments

Python 3.12+

Kwik stands on the shoulder of a couple of giants:

* [FastAPI](https://fastapi.tiangolo.com/): for the underlying REST API server.
* [Pydantic](https://docs.pydantic.dev/1.10/): for the data validation and serialization.
* [SQLAlchemy](https://www.sqlalchemy.org/): for the ORM part.

## Installation

```console
$ uv add kwik
```

It will install Kwik and all its dependencies.

## Quick Start

### Basic Usage

```python
# main.py
from kwik import Kwik, api_router
from kwik.settings import BaseKwikSettings
from kwik.crud import AutoCRUD
from kwik.models import Base, RecordInfoMixin
from sqlalchemy import Column, String
from pydantic import BaseModel

# 1. Define your model
class Product(Base, RecordInfoMixin):
    __tablename__ = "products"
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)

# 2. Define your schemas
class ProductCreate(BaseModel):
    name: str
    category: str

class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None

# 3. Create CRUD with automatic operations
from kwik.crud.context import UserCtx

class ProductCRUD(AutoCRUD[UserCtx, Product, ProductCreate, ProductUpdate, int]):
    pass

product_crud = ProductCRUD()

# 4. Configure your settings (optional)
class MySettings(BaseKwikSettings):
    PROJECT_NAME: str = "My Product API"

# 5. Create and configure Kwik application
settings = MySettings()
app = Kwik(settings=settings, api_router=api_router)
```

### Run it

```console
$ kwik
```

If Kwik is started in this way, it automatically creates a development server on port `8080`, with hot-reloading enabled.

### Check it

Open your browser at http://localhost:8080/docs.

You will see the automatic interactive API documentation, showing the built-in endpoints and schemas.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/dmezzogori/kwik.git
cd kwik

# Install dependencies using uv
uv sync

# Start development server with hot reload
kwik
```

### Testing

```bash
# Run all tests with coverage (testcontainers automatically manages PostgreSQL)
pytest --cov=src/kwik --cov-report=term-missing

# Run tests in parallel (faster)
pytest -n auto

# Run specific test file
pytest tests/test_crud_users.py

# Run only unit tests (skip integration tests)
pytest -m "not integration"
```

**Note**: Tests use testcontainers to automatically manage the PostgreSQL database. No manual database setup required.

### Code Quality

```bash
# Run linter and formatter
ruff check
ruff format

# Fix auto-fixable issues
ruff check --fix
```

### Documentation

```bash
# Start documentation website locally
cd docs
docker compose up

# Access at http://localhost:8000
```

### Contributing

1. Create a feature branch (`git checkout -b feature/your-feature-name`)
2. Make your changes following the existing code style
3. Add tests for new functionality
4. Run tests and ensure they pass
5. Run linting and fix any issues
6. Commit your changes (`git commit -am '<Your commit message>'`)
7. Push to the branch (`git push origin feature/your-feature-name`)
8. Create a Pull Request

## License

This project is licensed under the terms of the MIT license.
