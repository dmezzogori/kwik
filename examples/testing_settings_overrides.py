"""
Example usage of settings override context managers for testing.

This example demonstrates how to use the various settings override utilities
in Kwik for clean, isolated testing of configuration-dependent code.
"""

from kwik.core import (
    mock_settings,
    override_settings,
    with_debug_mode,
    with_production_mode,
    with_test_database,
)
from kwik.core.settings import BaseKwikSettings, configure_kwik, get_settings


def example_basic_override():
    """Example: Basic settings override for testing."""
    print("=== Basic Settings Override ===")

    # Original settings
    original = get_settings()
    print(f"Original PROJECT_NAME: {original.PROJECT_NAME}")
    print(f"Original DEBUG: {original.DEBUG}")

    # Override specific settings for a test
    with override_settings(PROJECT_NAME="test-app", DEBUG=True) as test_settings:
        print(f"Test PROJECT_NAME: {test_settings.PROJECT_NAME}")
        print(f"Test DEBUG: {test_settings.DEBUG}")

        # All other settings remain unchanged
        print(f"Database URI unchanged: {test_settings.SQLALCHEMY_DATABASE_URI}")

    # Settings are automatically restored
    restored = get_settings()
    print(f"Restored PROJECT_NAME: {restored.PROJECT_NAME}")
    print(f"Restored DEBUG: {restored.DEBUG}")
    print()


def example_nested_overrides():
    """Example: Nested overrides for testing different contexts."""
    print("=== Nested Settings Overrides ===")

    with override_settings(PROJECT_NAME="outer-test", DEBUG=False) as outer:
        print(f"Outer context - PROJECT_NAME: {outer.PROJECT_NAME}, DEBUG: {outer.DEBUG}")

        with override_settings(PROJECT_NAME="inner-test", BACKEND_PORT=9999) as inner:
            print(
                f"Inner context - PROJECT_NAME: {inner.PROJECT_NAME}, DEBUG: {inner.DEBUG}, PORT: {inner.BACKEND_PORT}"
            )

        # Back to outer context
        restored_outer = get_settings()
        print(f"Back to outer - PROJECT_NAME: {restored_outer.PROJECT_NAME}, DEBUG: {restored_outer.DEBUG}")

    print()


def example_mocked_settings():
    """Example: Using mocked settings for lightweight testing."""
    print("=== Mocked Settings (Lightweight) ===")

    original = get_settings()
    print(f"Original SECRET_KEY: {original.SECRET_KEY[:10]}...")

    # Mock specific attributes without recreating the entire settings
    with mock_settings(SECRET_KEY="test-secret-key", BACKEND_PORT=7777) as mocked:
        print(f"Mocked SECRET_KEY: {mocked.SECRET_KEY}")
        print(f"Mocked BACKEND_PORT: {mocked.BACKEND_PORT}")

        # Same instance, just mocked attributes
        print(f"Same instance: {mocked is original}")

    # Original values restored
    print(f"Restored SECRET_KEY: {original.SECRET_KEY[:10]}...")
    print()


def example_custom_settings_class():
    """Example: Using overrides with custom settings classes."""
    print("=== Custom Settings Class Override ===")

    class TestSettings(BaseKwikSettings):
        TEST_MODE: bool = False
        API_VERSION: str = "v1"
        MAX_CONNECTIONS: int = 100

    # Configure Kwik to use custom settings
    configure_kwik(settings_class=TestSettings)

    with override_settings(
        TEST_MODE=True, API_VERSION="v2", MAX_CONNECTIONS=50, PROJECT_NAME="custom-test"
    ) as settings:
        print(f"Custom settings class: {type(settings).__name__}")
        print(f"TEST_MODE: {settings.TEST_MODE}")
        print(f"API_VERSION: {settings.API_VERSION}")
        print(f"MAX_CONNECTIONS: {settings.MAX_CONNECTIONS}")
        print(f"PROJECT_NAME: {settings.PROJECT_NAME}")

    print()


def example_convenience_functions():
    """Example: Using convenience functions for common test scenarios."""
    print("=== Convenience Functions ===")

    # Test database configuration
    print("Test Database Configuration:")
    with with_test_database() as db_settings:
        print(f"  Test DB: {db_settings.POSTGRES_DB}")
        print(f"  Test Mode: {db_settings.TEST_ENV}")
        print(f"  Database URI: {db_settings.SQLALCHEMY_DATABASE_URI}")

    # Debug mode configuration
    print("\nDebug Mode Configuration:")
    with with_debug_mode() as debug_settings:
        print(f"  DEBUG: {debug_settings.DEBUG}")
        print(f"  LOG_LEVEL: {debug_settings.LOG_LEVEL}")
        print(f"  APP_ENV: {debug_settings.APP_ENV}")

    # Production mode configuration
    print("\nProduction Mode Configuration:")
    with with_production_mode() as prod_settings:
        print(f"  DEBUG: {prod_settings.DEBUG}")
        print(f"  LOG_LEVEL: {prod_settings.LOG_LEVEL}")
        print(f"  APP_ENV: {prod_settings.APP_ENV}")
        print(f"  HOTRELOAD: {prod_settings.HOTRELOAD}")

    # Convenience functions with additional overrides
    print("\nTest Database with Additional Overrides:")
    with with_test_database(ENABLE_SOFT_DELETE=True, POSTGRES_PORT="5433") as custom_db:
        print(f"  Test DB: {custom_db.POSTGRES_DB}")
        print(f"  Soft Delete: {custom_db.ENABLE_SOFT_DELETE}")
        print(f"  Port: {custom_db.POSTGRES_PORT}")

    print()


def example_testing_configuration_dependent_code():
    """Example: Testing code that depends on configuration."""
    print("=== Testing Configuration-Dependent Code ===")

    def get_api_url():
        """Example function that depends on settings."""
        settings = get_settings()
        protocol = "https" if settings.APP_ENV == "production" else "http"
        return f"{protocol}://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}{settings.API_V1_STR}"

    def get_database_pool_size():
        """Example function that returns different pool sizes based on environment."""
        settings = get_settings()
        if settings.DEBUG:
            return min(5, settings.POSTGRES_MAX_CONNECTIONS)
        return settings.POSTGRES_MAX_CONNECTIONS

    # Test API URL generation in different environments
    with with_production_mode(BACKEND_HOST="api.example.com", BACKEND_PORT=443) as prod:
        api_url = get_api_url()
        print(f"Production API URL: {api_url}")

    with with_debug_mode(BACKEND_HOST="localhost", BACKEND_PORT=8080) as debug:
        api_url = get_api_url()
        print(f"Debug API URL: {api_url}")

    # Test database pool sizing
    with override_settings(DEBUG=True, POSTGRES_MAX_CONNECTIONS=200) as debug_db:
        pool_size = get_database_pool_size()
        print(f"Debug pool size (capped at 5): {pool_size}")

    with override_settings(DEBUG=False, POSTGRES_MAX_CONNECTIONS=200) as prod_db:
        pool_size = get_database_pool_size()
        print(f"Production pool size: {pool_size}")

    print()


def example_complex_test_scenario():
    """Example: Complex testing scenario with multiple overrides."""
    print("=== Complex Test Scenario ===")

    def simulate_user_registration_service():
        """Simulate a service that behaves differently based on configuration."""
        settings = get_settings()

        if not settings.USERS_OPEN_REGISTRATION:
            return {"status": "error", "message": "Registration is closed"}

        if settings.DEBUG:
            # In debug mode, bypass email verification
            return {"status": "success", "user_id": 123, "verified": True}
        # In production, require email verification
        return {"status": "pending", "user_id": 123, "verified": False}

    # Test with registration disabled
    with override_settings(USERS_OPEN_REGISTRATION=False) as closed_reg:
        result = simulate_user_registration_service()
        print(f"Registration closed: {result}")

    # Test with debug mode (auto-verification)
    with with_debug_mode(USERS_OPEN_REGISTRATION=True) as debug_reg:
        result = simulate_user_registration_service()
        print(f"Debug registration: {result}")

    # Test with production mode (verification required)
    with with_production_mode(USERS_OPEN_REGISTRATION=True) as prod_reg:
        result = simulate_user_registration_service()
        print(f"Production registration: {result}")

    print()


if __name__ == "__main__":
    print("Kwik Settings Override Examples")
    print("=" * 40)
    print()

    # Reset to clean state
    from kwik.core.settings import reset_settings

    reset_settings()

    # Run all examples
    example_basic_override()
    example_nested_overrides()
    example_mocked_settings()
    example_custom_settings_class()
    example_convenience_functions()
    example_testing_configuration_dependent_code()
    example_complex_test_scenario()

    print("All examples completed successfully!")
