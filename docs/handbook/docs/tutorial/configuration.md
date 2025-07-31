# Configuration

Kwik provides a powerful and extensible configuration system that supports multiple configuration sources and allows you to extend settings with your own custom fields. The system is built on <a href="https://pydantic-docs.helpmanual.io/" class="external-link" target="_blank">Pydantic</a> for validation and type safety.

## Configuration Methods

Kwik supports multiple ways to configure your application:

1. **Environment Variables** (Default & Highest Priority)
2. **Programmatic Configuration** (Dictionary-based)
3. **Configuration Files** (JSON/YAML)
4. **Custom .env Files**

!!! tip "Priority Order"
    When multiple configuration sources are used, they are merged with the following priority (highest to lowest):
    
    1. Environment variables
    2. Programmatic configuration (dictionaries)
    3. Configuration files (JSON/YAML)

!!! warning "Security Note"
    Environment variables are not secure for sensitive information. Use <a href="https://pydantic-docs.helpmanual.io/usage/settings/#secret-support" class="external-link" target="_blank">SecretStr</a> types for passwords, API keys, and other sensitive data.

## Basic Usage (Environment Variables)

The traditional way to configure Kwik using environment variables still works:

```bash
# .env file or environment variables
PROJECT_NAME=my_awesome_api
BACKEND_PORT=9000
DEBUG=false
POSTGRES_SERVER=localhost
POSTGRES_DB=my_database
```

```python
import kwik

# Settings are automatically loaded from environment variables
print(kwik.settings.PROJECT_NAME)  # "my_awesome_api"
print(kwik.settings.BACKEND_PORT)  # 9000
```

## Extended Settings with Custom Fields

You can now extend the base settings with your own custom fields:

```python
from kwik import BaseKwikSettings, configure_kwik
from pydantic import validator

class MyAppSettings(BaseKwikSettings):
    # Your custom settings
    FEATURE_ADVANCED_SEARCH: bool = False
    API_TIMEOUT: int = 30
    CACHE_TTL: int = 300
    EXTERNAL_API_URL: str = "https://api.example.com"
    
    @validator("API_TIMEOUT")
    def validate_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("API timeout must be positive")
        return v

# Configure Kwik to use your extended settings
configure_kwik(settings_class=MyAppSettings)

# Now use your app normally
import kwik
app = kwik.Kwik(api_router)

# Access both standard and custom settings
print(kwik.settings.PROJECT_NAME)           # Standard setting
print(kwik.settings.FEATURE_ADVANCED_SEARCH) # Your custom setting
```

## Programmatic Configuration

Configure your application with dictionaries instead of environment variables:

```python
from kwik import configure_kwik

configure_kwik(
    settings_class=MyAppSettings,
    config_dict={
        "PROJECT_NAME": "my_api",
        "BACKEND_PORT": 8000,
        "FEATURE_ADVANCED_SEARCH": True,
        "API_TIMEOUT": 60,
        "DEBUG": False,
    }
)
```

## Configuration Files

### JSON Configuration

```json
{
    "PROJECT_NAME": "my_api",
    "BACKEND_PORT": 8000,
    "DEBUG": false,
    "FEATURE_ADVANCED_SEARCH": true,
    "API_TIMEOUT": 45
}
```

```python
from kwik import configure_kwik

configure_kwik(
    settings_class=MyAppSettings,
    config_file="config.json"
)
```

### YAML Configuration

```yaml
PROJECT_NAME: my_api
BACKEND_PORT: 8000
DEBUG: false
FEATURE_ADVANCED_SEARCH: true
API_TIMEOUT: 45
```

```python
from kwik import configure_kwik

# Requires PyYAML: pip install pyyaml
configure_kwik(
    settings_class=MyAppSettings,
    config_file="config.yaml"
)
```

## Multiple Configuration Sources

You can combine multiple configuration sources. Sources are merged with environment variables taking the highest priority:

```python
from kwik import configure_kwik

configure_kwik(
    settings_class=MyAppSettings,
    config_file="base_config.json",      # Lowest priority
    config_dict={"DEBUG": True},         # Medium priority
    # Environment variables automatically have highest priority
)
```

## Environment-Specific Configuration

```python
class EnvironmentSettings(BaseKwikSettings):
    ENVIRONMENT: str = "development"
    DATABASE_POOL_SIZE: int = 5
    LOG_LEVEL: str = "INFO"
    
    @validator("DATABASE_POOL_SIZE")
    def adjust_pool_for_env(cls, v: int, values: dict) -> int:
        env = values.get("ENVIRONMENT", "development")
        if env == "production":
            return max(v, 20)  # Minimum 20 connections in production
        return min(v, 5)       # Maximum 5 connections in development

# Configure for different environments
if is_production:
    configure_kwik(
        settings_class=EnvironmentSettings,
        config_dict={"ENVIRONMENT": "production"}
    )
```

## Built-in Configuration Variables

The following configuration variables are available by default:

### General Settings
- `APP_ENV`: `"development"` - Application environment
- `SERVER_NAME`: `"backend"` - Server/service name  
- `BACKEND_HOST`: `"localhost"` - Application hostname
- `BACKEND_PORT`: `8080` - Application port
- `API_V1_STR`: `"/api/v1"` - API base path
- `PROJECT_NAME`: `"kwik"` - Project name
- `PROTOCOL`: `"http"` - Protocol scheme

### Security Settings  
- `SECRET_KEY`: *auto-generated* - Application secret key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: `11520` - Token expiration (8 days)
- `SERVER_HOST`: `"http://localhost"` - Server host URL
- `BACKEND_CORS_ORIGINS`: `[]` - CORS allowed origins

### Server Settings
- `BACKEND_WORKERS`: `1` - Number of worker processes
- `HOTRELOAD`: `False` - Enable hot reloading in development
- `DEBUG`: `False` - Enable debug mode
- `LOG_LEVEL`: `"INFO"` - Logging level
- `WEBSOCKET_ENABLED`: `False` - Enable WebSocket support

### Database Settings
- `POSTGRES_SERVER`: `"db"` - Database server hostname
- `POSTGRES_USER`: `"postgres"` - Database username  
- `POSTGRES_PASSWORD`: `"root"` - Database password
- `POSTGRES_DB`: `"db"` - Database name
- `POSTGRES_MAX_CONNECTIONS`: `100` - Maximum database connections
- `ENABLE_SOFT_DELETE`: `False` - Enable soft delete functionality
- `SQLALCHEMY_DATABASE_URI`: *auto-generated* - Full database connection string

### User Management
- `FIRST_SUPERUSER`: `"admin@example.com"` - Default admin email
- `FIRST_SUPERUSER_PASSWORD`: `"admin"` - Default admin password  
- `USERS_OPEN_REGISTRATION`: `False` - Allow open user registration

### Feature Flags
- `DB_LOGGER`: `True` - Enable database query logging
- `TEST_ENV`: `False` - Test environment flag
- `SENTRY_INTEGRATION_ENABLED`: `False` - Enable Sentry error tracking
- `WEBSERVICE_ENABLED`: `False` - Enable external web service integration

!!! note "Production Configuration"
    Default values are for development only. Always override them in production with appropriate values.

!!! tip "Case Sensitivity"
    Environment variable names are **case sensitive**. Use exactly the names shown above.

## Testing Configuration

For tests, you can easily override settings:

```python
import pytest
from kwik import configure_kwik, reset_settings

class TestSettings(BaseKwikSettings):
    DATABASE_URL: str = "sqlite:///:memory:"
    TESTING: bool = True

@pytest.fixture
def test_settings():
    reset_settings()
    configure_kwik(
        settings_class=TestSettings,
        config_dict={"LOG_LEVEL": "DEBUG"}
    )
    yield
    reset_settings()

def test_my_feature(test_settings):
    import kwik
    assert kwik.settings.TESTING is True
```
