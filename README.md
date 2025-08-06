# Kwik

<div align="center">
<img src="docs/handbook/docs/img/logo.png" alt="Kwik Logo" width="200">
</div>

---

**Documentation**: https://kwik.rocks

**Repository**: https://github.com/dmezzogori/kwik

---

Kwik is a web framework for building modern, batteries-included, RESTful backends with Python 3.12+.
Kwik is based on FastAPI, builds upon it and delivers an opinionated concise, business-oriented API.

> :warning:
> While Kwik is in active development, and already used for production, it is still in a **pre-release state**.
> **The API is subject to change**, and the documentation is not complete yet.

## Key Features

### 🛠️ Advanced Settings Management

Multi-source configuration system supporting environment variables, files, and programmatic configuration with automatic validation.

```python
from kwik.core.settings import BaseKwikSettings, configure_kwik

class MyAppSettings(BaseKwikSettings):
    CUSTOM_API_KEY: str = "default-key"
    MAX_WORKERS: int = 4

# Configure with custom settings class
configure_kwik(
    settings_class=MyAppSettings,
    config_file="config.json",
    env_file=".env.production"
)
```

### 🚀 AutoCRUD System

Generic CRUD operations with automatic type inference, built-in pagination, filtering, and sorting.

```python
from kwik.crud.auto_crud import AutoCRUD
from kwik import models, schemas

class ProductCRUD(AutoCRUD[models.Product, schemas.ProductCreate, schemas.ProductUpdate]):
    pass

product_crud = ProductCRUD()

# Automatic pagination and sorting
total, products = product_crud.get_multi(
    skip=0, limit=10, 
    sort=[("name", "asc"), ("created_at", "desc")],
    category="electronics"
)
```

### 💉 Automatic Dependency Injection

Database sessions and current user automatically injected via context variables - no manual dependency management needed.

```python
class MyAutoCRUD(AutoCRUD[MyModel, MyCreate, MyUpdate]):
    def custom_method(self):
        # self.db automatically available (database session)
        # self.user automatically available (current authenticated user)
        return self.db.query(MyModel).filter_by(owner_id=self.user.id).all()
```

### 📊 SQLAlchemy Mixins

Pre-built mixins for common database patterns with automatic configuration.

```python
from kwik.database.mixins import RecordInfoMixin
from kwik.database.base import Base
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
from kwik.crud.users import users

# Check permissions
if users.has_permissions(user_id=user.id, permissions=["product.create", "product.update"]):
    # User has required permissions
    pass

# Assign roles
users.assign_role(user_id=user.id, role_id=admin_role.id)

# Get all user permissions
permissions = users.get_permissions(user_id=user.id)
```

### 📄 Pagination & Sorting Utilities

Ready-to-use pagination schemas and sorting dependencies for clean API endpoints.

```python
from fastapi import APIRouter
from kwik.schemas.pagination import Paginated
from kwik.api.deps.sorting_query import SortingQuery

router = APIRouter()

@router.get("/products", response_model=Paginated[ProductResponse])
def get_products(skip: int = 0, limit: int = 10, sort: SortingQuery = None):
    total, products = product_crud.get_multi(skip=skip, limit=limit, sort=sort)
    return {"total": total, "data": products}

# API usage: GET /products?sort=name:asc,created_at:desc
```

### 🔍 Automatic Audit Logging

Built-in request/response auditing with user tracking and performance monitoring.

```python
from kwik.routers.auditor import AuditorRouter

# All routes automatically logged with user context, timing, and request details
router = AuditorRouter(prefix="/api/v1/products")

@router.get("/")
def get_products():
    # Automatically logged: user, request details, response time, etc.
    return products
```

## Acknowledgments

Python 3.12+

Kwik stands on the shoulder of a couple of giants:

* [FastAPI](https://fastapi.tiangolo.com/): for the web parts.
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
from kwik.core.settings import BaseKwikSettings, configure_kwik
from kwik.crud.auto_crud import AutoCRUD
from kwik.database.base import Base
from kwik.database.mixins import RecordInfoMixin
from sqlalchemy import Column, String
import pydantic

# 1. Define your model
class Product(Base, RecordInfoMixin):
    __tablename__ = "products"
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)

# 2. Define your schemas
class ProductCreate(pydantic.BaseModel):
    name: str
    category: str

class ProductUpdate(pydantic.BaseModel):
    name: str | None = None
    category: str | None = None

# 3. Create CRUD with automatic operations
class ProductCRUD(AutoCRUD[Product, ProductCreate, ProductUpdate]):
    pass

product_crud = ProductCRUD()

# 4. Configure your settings (optional)
class MySettings(BaseKwikSettings):
    PROJECT_NAME: str = "My Product API"

configure_kwik(settings_class=MySettings)
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
ruff format .

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
