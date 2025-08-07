"""
Demo script for configuration dry-run validation.

This example demonstrates how to use the dry-run validator in CI/CD pipelines
to catch configuration errors before deployment.
"""

from kwik.core.dry_run import validate_config


def demo_basic_validation():
    """Demo: Basic configuration validation."""
    print("=== Basic Configuration Validation ===")

    # Valid configuration
    config = {
        "PROJECT_NAME": "demo-app",
        "SECRET_KEY": "demo-secret-key-strong-enough",
        "APP_ENV": "production",
        "BACKEND_PORT": 8080,
    }

    is_valid, report = validate_config(config_dict=config)
    print(f"Valid: {is_valid}")
    print(report)
    print()


def demo_invalid_configuration():
    """Demo: Invalid configuration that would fail deployment."""
    print("=== Invalid Configuration Detection ===")

    # Invalid configuration with multiple issues
    config = {
        "PROJECT_NAME": "demo-app",
        "SECRET_KEY": "weak",  # Too short
        "APP_ENV": "production",
        "BACKEND_PORT": 99999,  # Invalid port
        "SQLALCHEMY_DATABASE_URI": "mysql://bad-format",  # Non-standard URI
    }

    is_valid, report = validate_config(config_dict=config)
    print(f"Valid: {is_valid}")
    print(report)
    print()


def demo_with_profiles():
    """Demo: Validation with hierarchical profiles."""
    print("=== Hierarchical Profiles Validation ===")

    # This would load base.json + production.json + local.json if they exist
    is_valid, report = validate_config(profiles_enabled=True, profiles_dir="config", environment="production")

    print(f"Valid: {is_valid}")
    print(report)
    print()


def demo_with_secrets():
    """Demo: Validation with secrets system."""
    print("=== Secrets System Validation ===")

    config = {
        "PROJECT_NAME": "secrets-demo",
        "SECRET_KEY": "secret://env/DEMO_SECRET_KEY",  # Secret reference
        "DATABASE_PASSWORD": "secret://local/DB_PASSWORD",
    }

    is_valid, report = validate_config(config_dict=config, secrets_enabled=True)

    print(f"Valid: {is_valid}")
    print(report)
    print()


def demo_ci_cd_usage():
    """Demo: How to use in CI/CD pipelines."""
    print("=== CI/CD Pipeline Usage ===")

    print("Environment variables for CI/CD:")
    print("  KWIK_PROFILES_ENABLED=true")
    print("  KWIK_ENV=production")
    print("  KWIK_SECRETS_ENABLED=true")
    print()

    print("CLI command:")
    print("  python -m kwik.core.dry_run")
    print()

    print("Exit codes:")
    print("  0 = Configuration valid")
    print("  1 = Configuration errors found")
    print()

    print("Example CI/CD script:")
    print("""
  # .github/workflows/config-validation.yml
  - name: Validate Configuration
    run: |
      export KWIK_PROFILES_ENABLED=true
      export KWIK_ENV=production
      export KWIK_SECRETS_ENABLED=true
      python -m kwik.core.dry_run
    """)


if __name__ == "__main__":
    print("Kwik Configuration Dry-Run Validation Demo")
    print("=" * 50)
    print()

    demo_basic_validation()
    demo_invalid_configuration()
    demo_with_profiles()
    demo_with_secrets()
    demo_ci_cd_usage()

    print("\nTo run the CLI directly:")
    print("python -m kwik.core.dry_run")
