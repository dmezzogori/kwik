---
title: Features
---

# Features

Kwik provides a comprehensive set of features for building modern RESTful APIs with Python.

## 🚀 Core Features

### Extensible Configuration System
- **Custom Settings**: Extend `BaseKwikSettings` with your own configuration fields
- **Multiple Sources**: Environment variables, JSON/YAML files, programmatic configuration
- **Priority System**: Automatic merging with environment variables taking precedence
- **Type Safety**: Full Pydantic validation and type hints
- **Lazy Loading**: Settings only loaded when first accessed

```python
from kwik import BaseKwikSettings, configure_kwik

class MyAppSettings(BaseKwikSettings):
    FEATURE_X_ENABLED: bool = False
    API_TIMEOUT: int = 30
    CUSTOM_CACHE_TTL: int = 300

configure_kwik(settings_class=MyAppSettings)
```

### Built on FastAPI
- **High Performance**: Based on Starlette and Pydantic
- **Automatic Documentation**: Interactive API docs with Swagger UI
- **Type Safety**: Full type hints throughout
- **Modern Python**: Uses Python 3.11+ features

### Database Integration
- **SQLAlchemy ORM**: Powerful database abstraction
- **Async Support**: Full async/await support with AsyncPG
- **Migration Support**: Alembic integration for database migrations
- **Connection Pooling**: Optimized database connection management
- **Soft Delete**: Built-in soft delete pattern support
- **Automatic Audit**: Automatic audit trail for model changes

### Authentication & Security
- **JWT Tokens**: Secure authentication with JSON Web Tokens (OAuth2.0 based)
- **Permission System**: Flexible role-based access control
- **CORS Support**: Cross-origin resource sharing configuration
- **Security Headers**: Automatic security header management

### Developer Experience
- **Hot Reloading**: Automatic code reloading during development
- **Interactive Docs**: Automatic API documentation generation
- **Type Safety**: Full type checking with mypy support
- **Testing Support**: Easy testing with pytest integration

## 🔧 Configuration Flexibility

### Environment Variables (Traditional)
```bash
PROJECT_NAME=my_api
BACKEND_PORT=9000
DEBUG=false
```

### Programmatic Configuration
```python
configure_kwik(config_dict={
    "PROJECT_NAME": "my_api",
    "BACKEND_PORT": 8000,
    "DEBUG": True,
})
```

### JSON/YAML Configuration Files
```json
{
    "PROJECT_NAME": "my_api",
    "BACKEND_PORT": 8000,
    "DEBUG": false
}
```

### Multiple Sources with Priority
```python
configure_kwik(
    config_file="base_config.json",      # Lowest priority
    config_dict={"DEBUG": True},         # Medium priority
    # Environment variables automatically highest priority
)
```

## 🏗️ Architecture

### Modular Design
- **API Layer**: FastAPI-based route handling
- **Business Logic**: Clean separation of concerns
- **Data Layer**: SQLAlchemy models and CRUD operations
- **Configuration**: Centralized settings management

### Dependency Injection
- **Database Connections**: Automatic injection with transaction management
- **User Credentials**: Automatic injection in request-response cycle
- **Custom Dependencies**: Easy integration of custom dependencies

### Extensibility
- **Custom Settings**: Add your own configuration fields
- **Custom Validators**: Pydantic-based validation logic
- **Plugin System**: Extend functionality with custom modules
- **Environment Adaptation**: Settings that adapt to different environments

## 🔐 Security Features

### Built-in Authentication & Authorization
- JWT token-based authentication
- Role-based access control
- Permission decorators
- User session management

### Security Best Practices
- Secure password hashing with bcrypt
- CORS configuration
- Request validation
- Input sanitization

## 📊 Development & Deployment

### Development Workflow
```bash
python -m kwik  # Starts with hot reloading
```

### Production Ready
- Gunicorn integration for production deployment
- Multi-worker support
- Process management
- Resource optimization

### Testing Support
- Built-in test fixtures
- Database testing setup
- Settings override for tests
- Async testing support