# Custom Settings and Configuration

Kwik's enhanced settings system allows you to extend the framework's configuration with your own custom settings fields, validation logic, and configuration sources.

## Creating Custom Settings Classes

Extend `BaseKwikSettings` to add your own configuration fields:

```python
from kwik import BaseKwikSettings, configure_kwik
from pydantic import validator
from typing import List

class MyAppSettings(BaseKwikSettings):
    """Custom settings for my application."""
    
    # Feature flags
    FEATURE_ADVANCED_SEARCH: bool = False
    FEATURE_REAL_TIME_UPDATES: bool = True
    FEATURE_BETA_UI: bool = False
    
    # API configuration
    EXTERNAL_API_URL: str = "https://api.example.com"
    API_TIMEOUT: int = 30
    API_RETRIES: int = 3
    API_RATE_LIMIT: int = 1000
    
    # Cache configuration
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300
    CACHE_MAX_SIZE: int = 1000
    CACHE_BACKEND: str = "memory"  # memory, redis, memcached
    
    # Business logic settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".jpg", ".png", ".pdf", ".docx"]
    NOTIFICATION_CHANNELS: List[str] = ["email", "sms"]
    
    # Custom validation
    @validator("API_TIMEOUT")
    def validate_api_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("API timeout must be positive")
        if v > 300:
            raise ValueError("API timeout cannot exceed 300 seconds")
        return v
    
    @validator("CACHE_BACKEND")
    def validate_cache_backend(cls, v: str) -> str:
        allowed = ["memory", "redis", "memcached"]
        if v not in allowed:
            raise ValueError(f"Cache backend must be one of: {allowed}")
        return v
    
    @validator("ALLOWED_FILE_TYPES")
    def validate_file_types(cls, v: List[str]) -> List[str]:
        for file_type in v:
            if not file_type.startswith("."):
                raise ValueError(f"File type must start with '.': {file_type}")
        return v

# Configure Kwik to use your custom settings
configure_kwik(settings_class=MyAppSettings)
```

## Environment-Aware Settings

Create settings that adapt based on the environment:

```python
from kwik import BaseKwikSettings, configure_kwik
from pydantic import validator
from typing import Any, Dict

class EnvironmentAwareSettings(BaseKwikSettings):
    """Settings that adapt to different environments."""
    
    ENVIRONMENT: str = "development"
    
    # Database settings that scale with environment
    DATABASE_POOL_SIZE: int = 5
    DATABASE_TIMEOUT: int = 30
    DATABASE_RETRY_ATTEMPTS: int = 3
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_TO_FILE: bool = False
    LOG_MAX_FILES: int = 5
    
    # Performance settings
    CACHE_TTL: int = 300
    WORKER_TIMEOUT: int = 30
    REQUEST_TIMEOUT: int = 30
    
    # Security settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    @validator("DATABASE_POOL_SIZE")
    def adjust_pool_size(cls, v: int, values: Dict[str, Any]) -> int:
        env = values.get("ENVIRONMENT", "development")
        if env == "production":
            return max(v, 20)  # Minimum 20 connections in production
        elif env == "development":
            return min(v, 5)   # Maximum 5 connections in development
        elif env == "testing":
            return 1           # Single connection for tests
        return v
    
    @validator("LOG_LEVEL")
    def adjust_log_level(cls, v: str, values: Dict[str, Any]) -> str:
        env = values.get("ENVIRONMENT", "development")
        if env == "production" and v == "DEBUG":
            return "INFO"  # No debug logging in production
        elif env == "testing":
            return "WARNING"  # Minimal logging in tests
        return v
    
    @validator("CACHE_TTL")
    def adjust_cache_ttl(cls, v: int, values: Dict[str, Any]) -> int:
        env = values.get("ENVIRONMENT", "development")
        if env == "production":
            return max(v, 3600)  # Minimum 1 hour in production
        elif env == "development":
            return min(v, 60)    # Maximum 1 minute in development
        return v
    
    @validator("RATE_LIMIT_REQUESTS")
    def adjust_rate_limit(cls, v: int, values: Dict[str, Any]) -> int:
        env = values.get("ENVIRONMENT", "development")
        if env == "production":
            return v
        elif env == "development":
            return v * 10  # More lenient in development
        elif env == "testing":
            return 999999  # Effectively unlimited in tests
        return v

# Configure for different environments
import os

environment = os.getenv("APP_ENV", "development")
configure_kwik(
    settings_class=EnvironmentAwareSettings,
    config_dict={"ENVIRONMENT": environment}
)
```

## Advanced Configuration Patterns

### Conditional Settings

```python
from kwik import BaseKwikSettings
from pydantic import validator, root_validator
from typing import Optional

class ConditionalSettings(BaseKwikSettings):
    """Settings with conditional logic."""
    
    # Email settings
    EMAIL_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Redis settings  
    REDIS_ENABLED: bool = False
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    
    # Monitoring settings
    MONITORING_ENABLED: bool = False
    SENTRY_DSN: Optional[str] = None
    DATADOG_API_KEY: Optional[str] = None
    
    @root_validator
    def validate_email_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate email configuration when email is enabled."""
        if values.get("EMAIL_ENABLED"):
            required_fields = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"]
            for field in required_fields:
                if not values.get(field):
                    raise ValueError(f"{field} is required when EMAIL_ENABLED is True")
        return values
    
    @root_validator
    def validate_redis_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Redis configuration when Redis is enabled."""
        if values.get("REDIS_ENABLED") and not values.get("REDIS_URL"):
            raise ValueError("REDIS_URL is required when REDIS_ENABLED is True")
        return values
    
    @root_validator
    def validate_monitoring_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate monitoring configuration when monitoring is enabled."""
        if values.get("MONITORING_ENABLED"):
            if not values.get("SENTRY_DSN") and not values.get("DATADOG_API_KEY"):
                raise ValueError("Either SENTRY_DSN or DATADOG_API_KEY is required when MONITORING_ENABLED is True")
        return values
```

### Computed Settings

```python
from kwik import BaseKwikSettings
from pydantic import validator, computed_field
from typing import List

class ComputedSettings(BaseKwikSettings):
    """Settings with computed fields."""
    
    # Base settings
    BACKEND_HOST: str = "localhost"
    BACKEND_PORT: int = 8080
    API_VERSION: str = "v1"
    USE_HTTPS: bool = False
    
    # Database settings
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "myapp"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    
    @property
    def BASE_URL(self) -> str:
        """Compute the base URL from host, port, and protocol."""
        protocol = "https" if self.USE_HTTPS else "http"
        return f"{protocol}://{self.BACKEND_HOST}:{self.BACKEND_PORT}"
    
    @property
    def API_BASE_URL(self) -> str:
        """Compute the API base URL."""
        return f"{self.BASE_URL}/api/{self.API_VERSION}"
    
    @property
    def DATABASE_URL(self) -> str:
        """Compute the full database URL."""
        return (f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Compute allowed hosts based on configuration."""
        hosts = [self.BACKEND_HOST]
        if self.BACKEND_HOST != "localhost":
            hosts.append("localhost")
        if self.USE_HTTPS:
            hosts.append(f"{self.BACKEND_HOST}:443")
        else:
            hosts.append(f"{self.BACKEND_HOST}:80")
        return hosts
```

## Configuration Sources

### Custom Configuration Sources

```python
from kwik.core.settings import ConfigurationSource
from typing import Any, Dict
import requests

class RemoteConfigSource(ConfigurationSource):
    """Load configuration from a remote service."""
    
    def __init__(self, url: str, api_key: str):
        self.url = url
        self.api_key = api_key
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from remote service."""
        try:
            response = requests.get(
                self.url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback to empty config if remote source fails
            print(f"Failed to load remote config: {e}")
            return {}
    
    @property
    def priority(self) -> int:
        """Remote config has medium priority."""
        return 2

class DatabaseConfigSource(ConfigurationSource):
    """Load configuration from database."""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from database."""
        # Implementation would connect to database
        # and fetch configuration values
        return {}
    
    @property
    def priority(self) -> int:
        """Database config has low priority."""
        return 3

# Use custom sources
from kwik import configure_kwik

configure_kwik(
    settings_class=MyAppSettings,
    sources=[
        EnvironmentSource(),  # Highest priority
        RemoteConfigSource("https://config.myapp.com/api/config", "api-key"),
        DatabaseConfigSource("postgresql://..."),  # Lowest priority
    ]
)
```

### Configuration Hierarchies

```python
from kwik import BaseKwikSettings, configure_kwik
import os

class HierarchicalSettings(BaseKwikSettings):
    """Settings that support configuration hierarchies."""
    
    CONFIG_HIERARCHY: str = "local"  # local, team, organization, global
    
    # Local settings (highest priority)
    LOCAL_CACHE_ENABLED: bool = True
    LOCAL_LOG_LEVEL: str = "DEBUG"
    
    # Team settings
    TEAM_SHARED_CACHE: bool = False
    TEAM_LOG_RETENTION: int = 7
    
    # Organization settings
    ORG_SECURITY_POLICY: str = "standard"
    ORG_COMPLIANCE_MODE: bool = False
    
    # Global settings (lowest priority)
    GLOBAL_RATE_LIMIT: int = 1000
    GLOBAL_TIMEOUT: int = 30

# Load configuration based on hierarchy
hierarchy = os.getenv("CONFIG_HIERARCHY", "local")

config_files = []
if hierarchy in ["global", "organization", "team", "local"]:
    config_files.append("config/global.json")
if hierarchy in ["organization", "team", "local"]:
    config_files.append("config/organization.json")
if hierarchy in ["team", "local"]:
    config_files.append("config/team.json")
if hierarchy == "local":
    config_files.append("config/local.json")

# Configure with multiple file sources
for config_file in config_files:
    if os.path.exists(config_file):
        configure_kwik(
            settings_class=HierarchicalSettings,
            config_file=config_file
        )
```

## Best Practices

### 1. Organize Settings by Feature

```python
from kwik import BaseKwikSettings
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    """Database-specific configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "myapp"
    user: str = "postgres"
    password: str = "password"
    pool_size: int = 10
    timeout: int = 30

class CacheConfig(BaseModel):
    """Cache-specific configuration."""
    enabled: bool = True
    backend: str = "memory"
    ttl: int = 300
    max_size: int = 1000

class APIConfig(BaseModel):
    """API-specific configuration."""
    timeout: int = 30
    retries: int = 3
    rate_limit: int = 1000
    base_url: str = "https://api.example.com"

class OrganizedSettings(BaseKwikSettings):
    """Well-organized settings using nested models."""
    
    database: DatabaseConfig = DatabaseConfig()
    cache: CacheConfig = CacheConfig()
    api: APIConfig = APIConfig()
    
    # Top-level application settings
    app_name: str = "My Application"
    debug: bool = False
    environment: str = "development"
```

### 2. Use Type Hints and Validation

```python
from kwik import BaseKwikSettings
from pydantic import validator, Field
from typing import List, Optional, Union
from enum import Enum

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class CacheBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    MEMCACHED = "memcached"

class TypedSettings(BaseKwikSettings):
    """Settings with proper typing and validation."""
    
    # Use enums for constrained choices
    log_level: LogLevel = LogLevel.INFO
    cache_backend: CacheBackend = CacheBackend.MEMORY
    
    # Use Field for additional constraints
    port: int = Field(default=8080, ge=1, le=65535)
    timeout: float = Field(default=30.0, gt=0, le=300)
    
    # Use Union for multiple allowed types
    database_url: Union[str, None] = None
    
    # Use List for collections
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    # Use Optional for nullable fields
    api_key: Optional[str] = None
    
    @validator("allowed_hosts")
    def validate_hosts(cls, v: List[str]) -> List[str]:
        for host in v:
            if not host or host.isspace():
                raise ValueError("Host cannot be empty")
        return v
```

### 3. Environment-Specific Defaults

```python
from kwik import BaseKwikSettings, configure_kwik
from pydantic import validator
import os

class SmartDefaults(BaseKwikSettings):
    """Settings with smart environment-specific defaults."""
    
    environment: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    
    # Defaults that adapt to environment
    debug: bool = Field(default_factory=lambda: os.getenv("APP_ENV", "development") == "development")
    log_level: str = Field(default_factory=lambda: "DEBUG" if os.getenv("APP_ENV") == "development" else "INFO")
    
    @validator("debug", pre=True, always=True)
    def set_debug_from_env(cls, v, values):
        env = values.get("environment", "development")
        if env == "production":
            return False
        return v if v is not None else (env == "development")
```

This advanced configuration system gives you complete control over your application's settings while maintaining type safety, validation, and easy testing capabilities.