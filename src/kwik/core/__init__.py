"""
Core framework package for kwik framework.

This package contains core framework components including configuration,
security utilities, and other foundational elements.
"""

# Export test utilities for easier imports
from kwik.core.test_overrides import (
    MockedSettingsContext,
    SettingsOverrideContext,
    TransactionalSettingsContext,
    mock_settings,
    override_settings,
    transactional_settings,
    with_debug_mode,
    with_production_mode,
    with_test_database,
)

__all__ = [
    # Test override utilities
    "SettingsOverrideContext",
    "MockedSettingsContext",
    "TransactionalSettingsContext",
    "override_settings",
    "mock_settings",
    "transactional_settings",
    "with_debug_mode",
    "with_production_mode",
    "with_test_database",
]
