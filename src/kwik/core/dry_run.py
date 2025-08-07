"""
Configuration dry-run validation for CI/CD pipelines.

This module provides validation of configuration without actually running the application,
allowing CI/CD pipelines to catch configuration errors before deployment.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from kwik.core.settings import BaseKwikSettings, SettingsFactory

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a configuration validation check."""

    level: ValidationLevel
    message: str
    field: str | None = None
    suggestion: str | None = None


class ConfigDryRunValidator:
    """Validator for configuration dry-run checks."""

    def __init__(self) -> None:
        """Initialize the dry-run validator."""
        self.results: list[ValidationResult] = []

    def validate_configuration(
        self,
        settings_class: type[BaseKwikSettings] | None = None,
        config_dict: dict[str, Any] | None = None,
        config_file: str | None = None,
        env_file: str | None = None,
        profiles_enabled: bool = False,
        profiles_dir: str = "config",
        environment: str | None = None,
        secrets_enabled: bool = False,
        cloud_secrets_enabled: bool = False,
    ) -> bool:
        """
        Validate configuration without running the application.

        Args:
            settings_class: Custom settings class to validate
            config_dict: Dictionary of configuration values
            config_file: Path to configuration file
            env_file: Path to .env file
            profiles_enabled: Whether to load hierarchical profiles
            profiles_dir: Directory containing profile files
            environment: Environment name for profile loading
            secrets_enabled: Whether secrets resolution is enabled
            cloud_secrets_enabled: Whether cloud secrets providers are enabled

        Returns:
            True if configuration is valid, False otherwise

        """
        self.results.clear()

        try:
            # Create a temporary factory for validation
            factory = SettingsFactory()

            # Configure the factory with provided options
            factory.configure(
                settings_class=settings_class,
                config_dict=config_dict,
                config_file=config_file,
                env_file=env_file,
                profiles_enabled=profiles_enabled,
                profiles_dir=profiles_dir,
                environment=environment,
                secrets_enabled=secrets_enabled,
                cloud_secrets_enabled=cloud_secrets_enabled,
            )

            # Attempt to create settings instance
            settings = factory.get_settings()

            # Perform additional validation checks
            self._validate_required_fields(settings)
            self._validate_field_types(settings)
            self._validate_cross_dependencies(settings)

            if secrets_enabled:
                self._validate_secrets_resolution(factory, settings)

            self._add_success_info(settings)

        except Exception as e:
            self.results.append(
                ValidationResult(
                    level=ValidationLevel.ERROR,
                    message=f"Configuration validation failed: {e}",
                    suggestion="Check your configuration files and environment variables",
                )
            )
            return False

        return not self.has_errors()

    def _validate_required_fields(self, settings: BaseKwikSettings) -> None:
        """Validate that required fields are present and not empty."""
        # Check PROJECT_NAME - should not be empty or default
        if not settings.PROJECT_NAME or settings.PROJECT_NAME.strip() == "" or settings.PROJECT_NAME == "kwik":
            if settings.PROJECT_NAME == "kwik":
                # Only warn for default value, don't fail
                self.results.append(
                    ValidationResult(
                        level=ValidationLevel.WARNING,
                        message="Using default PROJECT_NAME",
                        field="PROJECT_NAME",
                        suggestion="Set a specific PROJECT_NAME for your application",
                    )
                )
            else:
                self.results.append(
                    ValidationResult(
                        level=ValidationLevel.ERROR,
                        message="Project name is required",
                        field="PROJECT_NAME",
                        suggestion="Set PROJECT_NAME in your configuration",
                    )
                )

        # Check SECRET_KEY - should not be default or weak
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 10:
            self.results.append(
                ValidationResult(
                    level=ValidationLevel.ERROR,
                    message="SECRET_KEY is missing or too short",
                    field="SECRET_KEY",
                    suggestion="Set a strong SECRET_KEY (at least 10 characters)",
                )
            )

    def _validate_field_types(self, settings: BaseKwikSettings) -> None:
        """Validate field types and formats."""
        # Check database URI format
        db_uri = settings.SQLALCHEMY_DATABASE_URI
        if db_uri and not db_uri.startswith(("postgresql://", "sqlite:///")):
            self.results.append(
                ValidationResult(
                    level=ValidationLevel.WARNING,
                    message="Database URI should start with postgresql:// or sqlite:///",
                    field="SQLALCHEMY_DATABASE_URI",
                    suggestion="Check your database connection string format",
                )
            )

        # Check port ranges
        if not (1 <= settings.BACKEND_PORT <= 65535):
            self.results.append(
                ValidationResult(
                    level=ValidationLevel.ERROR,
                    message=f"BACKEND_PORT {settings.BACKEND_PORT} is not a valid port number",
                    field="BACKEND_PORT",
                    suggestion="Use a port number between 1 and 65535",
                )
            )

    def _validate_cross_dependencies(self, settings: BaseKwikSettings) -> None:
        """Validate cross-field dependencies."""
        # Production environment checks
        if settings.APP_ENV == "production":
            if settings.DEBUG:
                self.results.append(
                    ValidationResult(
                        level=ValidationLevel.WARNING,
                        message="DEBUG is enabled in production environment",
                        field="DEBUG",
                        suggestion="Set DEBUG=False for production",
                    )
                )

            # Check for weak/default secret keys in production
            weak_secrets = ["admin", "secret", "password", "test", "default"]
            if settings.SECRET_KEY in weak_secrets or len(settings.SECRET_KEY) < 32:
                self.results.append(
                    ValidationResult(
                        level=ValidationLevel.ERROR,
                        message="Weak or default SECRET_KEY detected in production",
                        field="SECRET_KEY",
                        suggestion="Use a strong, unique secret key for production (at least 32 characters)",
                    )
                )

    def _validate_secrets_resolution(self, factory: SettingsFactory, settings: BaseKwikSettings) -> None:
        """Validate that secrets can be resolved (without fetching actual values)."""
        try:
            # Get the merged config to check for secret references
            config = factory._registry.get_merged_config()

            secret_refs = []
            for key, value in config.items():
                if isinstance(value, str) and value.startswith("secret://"):
                    secret_refs.append((key, value))

            if secret_refs:
                self.results.append(
                    ValidationResult(
                        level=ValidationLevel.INFO,
                        message=f"Found {len(secret_refs)} secret reference(s) in configuration",
                        suggestion="Ensure all secret providers are properly configured",
                    )
                )

                # Check if secrets system is available
                try:
                    from kwik.core.secrets import get_secrets_manager  # noqa: PLC0415

                    manager = get_secrets_manager()
                    providers = manager.list_providers()

                    available_providers = [p for p in providers if p["available"]]
                    if not available_providers:
                        self.results.append(
                            ValidationResult(
                                level=ValidationLevel.WARNING,
                                message="No secrets providers are available",
                                suggestion="Configure at least one secrets provider (environment variables, local files, or cloud)",
                            )
                        )

                except ImportError:
                    self.results.append(
                        ValidationResult(
                            level=ValidationLevel.WARNING,
                            message="Secrets system not available",
                            suggestion="Install required dependencies for secrets management",
                        )
                    )

        except Exception as e:
            self.results.append(
                ValidationResult(level=ValidationLevel.WARNING, message=f"Could not validate secrets resolution: {e}")
            )

    def _add_success_info(self, settings: BaseKwikSettings) -> None:
        """Add informational messages about successful validation."""
        self.results.append(
            ValidationResult(
                level=ValidationLevel.INFO,
                message=f"Configuration validated successfully for environment: {settings.APP_ENV}",
            )
        )

        self.results.append(
            ValidationResult(
                level=ValidationLevel.INFO,
                message=f"Using database: {settings.SQLALCHEMY_DATABASE_URI.split('@')[-1] if settings.SQLALCHEMY_DATABASE_URI else 'Not configured'}",
            )
        )

    def has_errors(self) -> bool:
        """Check if validation found any errors."""
        return any(result.level == ValidationLevel.ERROR for result in self.results)

    def has_warnings(self) -> bool:
        """Check if validation found any warnings."""
        return any(result.level == ValidationLevel.WARNING for result in self.results)

    def get_report(self, format_type: str = "text") -> str:
        """
        Get validation report in specified format.

        Args:
            format_type: Output format ('text', 'json')

        Returns:
            Formatted validation report

        """
        if format_type == "json":
            return self._get_json_report()
        return self._get_text_report()

    def _get_text_report(self) -> str:
        """Get human-readable text report."""
        if not self.results:
            return "No validation results available."

        lines = ["Configuration Validation Report", "=" * 35, ""]

        # Group by level
        errors = [r for r in self.results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in self.results if r.level == ValidationLevel.WARNING]
        info = [r for r in self.results if r.level == ValidationLevel.INFO]

        if errors:
            lines.append("❌ ERRORS:")
            for result in errors:
                lines.append(f"  • {result.message}")
                if result.field:
                    lines.append(f"    Field: {result.field}")
                if result.suggestion:
                    lines.append(f"    Suggestion: {result.suggestion}")
                lines.append("")

        if warnings:
            lines.append("⚠️  WARNINGS:")
            for result in warnings:
                lines.append(f"  • {result.message}")
                if result.field:
                    lines.append(f"    Field: {result.field}")
                if result.suggestion:
                    lines.append(f"    Suggestion: {result.suggestion}")
                lines.append("")

        if info:
            lines.append("ℹ️  INFO:")
            for result in info:
                lines.append(f"  • {result.message}")
                lines.append("")

        # Summary
        lines.extend(
            [
                "SUMMARY:",
                f"  Errors: {len(errors)}",
                f"  Warnings: {len(warnings)}",
                f"  Status: {'❌ FAILED' if errors else '✅ PASSED'}",
            ]
        )

        return "\n".join(lines)

    def _get_json_report(self) -> str:
        """Get JSON-formatted report."""
        report = {
            "validation_results": [
                {
                    "level": result.level.value,
                    "message": result.message,
                    "field": result.field,
                    "suggestion": result.suggestion,
                }
                for result in self.results
            ],
            "summary": {
                "errors": len([r for r in self.results if r.level == ValidationLevel.ERROR]),
                "warnings": len([r for r in self.results if r.level == ValidationLevel.WARNING]),
                "passed": not self.has_errors(),
            },
        }
        return json.dumps(report, indent=2)


def validate_config(**kwargs) -> tuple[bool, str]:
    """
    Convenience function to validate configuration.

    Args:
        **kwargs: Configuration parameters for validation

    Returns:
        Tuple of (is_valid, report_text)

    """
    validator = ConfigDryRunValidator()
    is_valid = validator.validate_configuration(**kwargs)
    report = validator.get_report()
    return is_valid, report


def dry_run_main() -> int:
    """
    Main entry point for dry-run validation CLI.

    Returns:
        Exit code (0 for success, 1 for validation errors)

    """
    import os

    # Simple CLI argument parsing (could be enhanced with argparse later)
    profiles_enabled = os.getenv("KWIK_PROFILES_ENABLED", "false").lower() == "true"
    environment = os.getenv("KWIK_ENV", "development")
    secrets_enabled = os.getenv("KWIK_SECRETS_ENABLED", "false").lower() == "true"

    print("🔍 Kwik Configuration Dry-Run Validation")
    print(f"Environment: {environment}")
    print(f"Profiles: {'enabled' if profiles_enabled else 'disabled'}")
    print(f"Secrets: {'enabled' if secrets_enabled else 'disabled'}")
    print("-" * 50)

    validator = ConfigDryRunValidator()
    is_valid = validator.validate_configuration(
        profiles_enabled=profiles_enabled,
        environment=environment,
        secrets_enabled=secrets_enabled,
    )

    print(validator.get_report())

    return 0 if is_valid else 1


if __name__ == "__main__":
    exit(dry_run_main())
