"""isort:skip_file."""

from __future__ import annotations

# Import the new settings system
from .core.settings import BaseKwikSettings, configure_kwik, get_settings

# For backward compatibility, create a lazy-loaded settings object
# This replaces the immediate Settings() instantiation with lazy loading
class SettingsProxy:
    """Proxy object that provides lazy loading of settings for backward compatibility."""
    
    def __getattr__(self, name: str):
        """Delegate attribute access to the actual settings instance."""
        return getattr(get_settings(), name)
        
    def __setattr__(self, name: str, value):
        """Delegate attribute setting to the actual settings instance."""
        return setattr(get_settings(), name, value)
        
    def __dir__(self):
        """Return available attributes from the settings instance."""
        return dir(get_settings())

# Create the lazy-loaded settings proxy for backward compatibility
settings = SettingsProxy()

# For backward compatibility, also expose the original Settings class
from .core.config import Settings

from . import database as database  # noqa: E402
from . import utils  # noqa: E402
from .api.api import api_router  # noqa: E402
from .api.deps import (  # noqa: E402
    FilterQuery,
    PaginatedQuery,
    SortingQuery,
    current_user,
    has_permission,
)
from .applications import Kwik, run  # noqa: E402
from .logger import logger  # noqa: E402
from .routers.autorouter import AutoRouter  # noqa: E402
from .websocket.deps import broadcast  # noqa: E402

__all__ = [
    "AutoRouter",
    "BaseKwikSettings",
    "FilterQuery",
    "Kwik",
    "PaginatedQuery",
    "Settings",
    "SortingQuery",
    "api_router",
    "broadcast",
    "configure_kwik",
    "current_user",
    "database",
    "has_permission",
    "logger",
    "run",
    "settings",
    "utils",
]
