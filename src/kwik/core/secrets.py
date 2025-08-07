"""
Unified secrets provider abstraction for Kwik framework.

This module provides a pluggable secrets management system that supports:
- Multiple provider backends (AWS, Azure, GCP, local)
- secret:// URI syntax for referencing secrets in configuration
- Automatic provider resolution and credential management
- Local development fallback system
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SecretResolutionError(Exception):
    """Raised when a secret cannot be resolved from any provider."""


class SecretProvider(ABC):
    """Abstract base class for secret providers."""

    @abstractmethod
    def get_secret(self, secret_name: str, **kwargs: Any) -> str:
        """
        Retrieve a secret value by name.

        Args:
            secret_name: Name or path of the secret
            **kwargs: Additional provider-specific parameters

        Returns:
            Secret value as string

        Raises:
            SecretResolutionError: If secret cannot be retrieved

        """

    @abstractmethod
    def supports_uri(self, uri: str) -> bool:
        """
        Check if this provider supports the given URI scheme.

        Args:
            uri: Secret URI to check

        Returns:
            True if provider can handle this URI

        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name of the provider."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (credentials configured, etc.)."""


class LocalSecretsProvider(SecretProvider):
    """
    Local secrets provider for development and testing.

    Supports multiple storage formats:
    - .env files with secrets
    - JSON files with secret mappings
    - Directory of secret files (one secret per file)
    """

    def __init__(self, secrets_path: str | Path | None = None) -> None:
        """
        Initialize local secrets provider.

        Args:
            secrets_path: Path to secrets file/directory (defaults to ./secrets)

        """
        self.secrets_path = Path(secrets_path or "secrets")
        self._cached_secrets: dict[str, str] = {}

    def get_secret(self, secret_name: str, **kwargs: Any) -> str:
        """Get secret from local storage."""
        if secret_name in self._cached_secrets:
            return self._cached_secrets[secret_name]

        secret_value = self._load_secret(secret_name)
        if secret_value is None:
            msg = f"Secret '{secret_name}' not found in local storage"
            raise SecretResolutionError(msg)

        self._cached_secrets[secret_name] = secret_value
        return secret_value

    def _load_secret(self, secret_name: str) -> str | None:
        """Load secret from various local storage formats."""
        if not self.secrets_path.exists():
            return None

        # Try directory structure (one file per secret)
        if self.secrets_path.is_dir():
            secret_file = self.secrets_path / secret_name
            if secret_file.exists() and secret_file.is_file():
                return secret_file.read_text(encoding="utf-8").strip()

            # Try with common extensions
            for ext in [".txt", ".secret", ""]:
                secret_file = self.secrets_path / f"{secret_name}{ext}"
                if secret_file.exists() and secret_file.is_file():
                    return secret_file.read_text(encoding="utf-8").strip()

        # Try as .env file
        if self.secrets_path.is_file() and self.secrets_path.suffix == ".env":
            return self._load_from_env_file(secret_name)

        # Try as JSON file
        if self.secrets_path.is_file() and self.secrets_path.suffix == ".json":
            return self._load_from_json_file(secret_name)

        return None

    def _load_from_env_file(self, secret_name: str) -> str | None:
        """Load secret from .env file format."""
        try:
            with self.secrets_path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if key.strip() == secret_name:
                            return value.strip().strip("\"'")
        except Exception as e:
            logger.warning(f"Error reading secrets from {self.secrets_path}: {e}")
        return None

    def _load_from_json_file(self, secret_name: str) -> str | None:
        """Load secret from JSON file format."""
        try:
            import json

            with self.secrets_path.open(encoding="utf-8") as f:
                secrets_data = json.load(f)
                return secrets_data.get(secret_name)
        except Exception as e:
            logger.warning(f"Error reading JSON secrets from {self.secrets_path}: {e}")
        return None

    def supports_uri(self, uri: str) -> bool:
        """Support secret://local/ and secret://file/ URIs."""
        parsed = urlparse(uri)
        return parsed.scheme == "secret" and parsed.netloc in ["local", "file"]

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "Local Secrets"

    @property
    def is_available(self) -> bool:
        """Local provider is always available."""
        return True

    def list_secrets(self) -> list[str]:
        """List available secrets for debugging."""
        secrets = []

        if not self.secrets_path.exists():
            return secrets

        if self.secrets_path.is_dir():
            for file_path in self.secrets_path.iterdir():
                if file_path.is_file():
                    secrets.append(file_path.stem)
        elif self.secrets_path.suffix == ".env":
            try:
                with self.secrets_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key = line.split("=", 1)[0].strip()
                            secrets.append(key)
            except Exception:
                pass
        elif self.secrets_path.suffix == ".json":
            try:
                import json

                with self.secrets_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        secrets.extend(data.keys())
            except Exception:
                pass

        return sorted(secrets)


class EnvironmentSecretsProvider(SecretProvider):
    """
    Environment variables secrets provider.

    Looks up secrets in environment variables with configurable prefixes.
    """

    def __init__(self, prefixes: list[str] | None = None) -> None:
        """
        Initialize environment secrets provider.

        Args:
            prefixes: List of environment variable prefixes to try

        """
        self.prefixes = prefixes or ["SECRET_", "KWIK_SECRET_", ""]

    def get_secret(self, secret_name: str, **kwargs: Any) -> str:
        """Get secret from environment variables."""
        for prefix in self.prefixes:
            env_var_name = f"{prefix}{secret_name.upper()}"
            value = os.getenv(env_var_name)
            if value is not None:
                return value

        # Try the secret name as-is
        value = os.getenv(secret_name.upper())
        if value is not None:
            return value

        msg = f"Secret '{secret_name}' not found in environment variables (tried prefixes: {self.prefixes})"
        raise SecretResolutionError(msg)

    def supports_uri(self, uri: str) -> bool:
        """Support secret://env/ URIs."""
        parsed = urlparse(uri)
        return parsed.scheme == "secret" and parsed.netloc == "env"

    @property
    def provider_name(self) -> str:
        """Provider name."""
        return "Environment Variables"

    @property
    def is_available(self) -> bool:
        """Environment provider is always available."""
        return True


class SecretsManager:
    """
    Central manager for secrets resolution with multiple provider support.

    Provides unified interface for resolving secrets from different providers
    and supports secret:// URI syntax in configuration files.
    """

    def __init__(self) -> None:
        """Initialize secrets manager."""
        self._providers: list[SecretProvider] = []
        self._secret_uri_pattern = re.compile(r"secret://([^/]+)/(.+)")
        self._setup_default_providers()

    def _setup_default_providers(self) -> None:
        """Set up default providers in priority order."""
        # Environment variables (highest priority)
        self.add_provider(EnvironmentSecretsProvider())

        # Local secrets (fallback for development)
        self.add_provider(LocalSecretsProvider())

    def add_provider(self, provider: SecretProvider) -> None:
        """
        Add a secrets provider.

        Args:
            provider: Provider instance to add

        """
        self._providers.append(provider)
        logger.debug(f"Added secrets provider: {provider.provider_name}")

    def remove_provider(self, provider_type: type[SecretProvider]) -> None:
        """
        Remove providers of a specific type.

        Args:
            provider_type: Type of provider to remove

        """
        self._providers = [p for p in self._providers if not isinstance(p, provider_type)]

    def get_secret(self, secret_ref: str, **kwargs: Any) -> str:
        """
        Resolve a secret by reference.

        Args:
            secret_ref: Secret reference (name or secret:// URI)
            **kwargs: Additional parameters passed to providers

        Returns:
            Secret value

        Raises:
            SecretResolutionError: If secret cannot be resolved

        """
        # Check if it's a secret:// URI
        if secret_ref.startswith("secret://"):
            return self._resolve_secret_uri(secret_ref, **kwargs)

        # Try all providers for simple secret name
        errors = []
        for provider in self._providers:
            if not provider.is_available:
                continue

            try:
                return provider.get_secret(secret_ref, **kwargs)
            except SecretResolutionError as e:
                errors.append(f"{provider.provider_name}: {e}")
                continue

        msg = f"Could not resolve secret '{secret_ref}' from any provider. Errors: {'; '.join(errors)}"
        raise SecretResolutionError(msg)

    def _resolve_secret_uri(self, uri: str, **kwargs: Any) -> str:
        """Resolve a secret:// URI using appropriate provider."""
        # Validate URI format first - must be secret://provider/secret_name
        if not uri.startswith("secret://") or uri.count("/") < 2:
            msg = f"Invalid secret URI format: {uri}"
            raise SecretResolutionError(msg)

        match = self._secret_uri_pattern.match(uri)
        if not match:
            msg = f"Invalid secret URI format: {uri}"
            raise SecretResolutionError(msg)

        provider_name, secret_name = match.groups()

        # Find provider that supports this URI
        for provider in self._providers:
            if provider.supports_uri(uri) and provider.is_available:
                try:
                    return provider.get_secret(secret_name, **kwargs)
                except SecretResolutionError:
                    continue

        msg = f"No available provider supports URI: {uri}"
        raise SecretResolutionError(msg)

    def resolve_config_secrets(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively resolve secret references in a configuration dictionary.

        Args:
            config: Configuration dictionary that may contain secret references

        Returns:
            Configuration with secrets resolved

        """
        resolved_config = {}

        for key, value in config.items():
            if isinstance(value, str) and (value.startswith("secret://") or self._looks_like_secret_ref(key, value)):
                try:
                    resolved_config[key] = self.get_secret(value)
                except SecretResolutionError as e:
                    logger.exception(f"Failed to resolve secret for '{key}': {e}")
                    # Keep original value as fallback
                    resolved_config[key] = value
            elif isinstance(value, dict):
                resolved_config[key] = self.resolve_config_secrets(value)
            elif isinstance(value, list):
                resolved_config[key] = [
                    self.resolve_config_secrets(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                resolved_config[key] = value

        return resolved_config

    def _looks_like_secret_ref(self, key: str, value: str) -> bool:
        """
        Heuristic to detect if a configuration value might be a secret reference.

        Args:
            key: Configuration key name
            value: Configuration value

        Returns:
            True if value looks like it might be a secret reference

        """
        # Check for common secret key patterns
        secret_key_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "api_key",
            "private_key",
            "auth_token",
            "access_key",
        ]

        key_lower = key.lower()
        if any(pattern in key_lower for pattern in secret_key_patterns):
            # Value looks like a reference (not actual secret data)
            return (
                (
                    len(value) < 100  # Reasonable reference length
                    and not value.startswith(("http://", "https://"))  # Not a URL
                    and "_" in value
                )
                or "-" in value
                or "/" in value  # Looks like identifier
            )

        return False

    def list_providers(self) -> list[dict[str, Any]]:
        """
        List all registered providers with their status.

        Returns:
            List of provider information dictionaries

        """
        return [
            {
                "name": provider.provider_name,
                "type": type(provider).__name__,
                "available": provider.is_available,
            }
            for provider in self._providers
        ]

    def get_provider_by_type(self, provider_type: type[SecretProvider]) -> SecretProvider | None:
        """
        Get provider instance by type.

        Args:
            provider_type: Type of provider to find

        Returns:
            Provider instance or None if not found

        """
        for provider in self._providers:
            if isinstance(provider, provider_type):
                return provider
        return None


# Global secrets manager instance
_secrets_manager = SecretsManager()


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager instance."""
    return _secrets_manager


def get_secret(secret_ref: str, **kwargs: Any) -> str:
    """
    Convenience function to get a secret using the global manager.

    Args:
        secret_ref: Secret reference (name or URI)
        **kwargs: Additional parameters

    Returns:
        Secret value

    """
    return _secrets_manager.get_secret(secret_ref, **kwargs)


def resolve_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """
    Convenience function to resolve secrets in configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with secrets resolved

    """
    return _secrets_manager.resolve_config_secrets(config)


def add_secrets_provider(provider: SecretProvider) -> None:
    """
    Add a secrets provider to the global manager.

    Args:
        provider: Provider instance to add

    """
    _secrets_manager.add_provider(provider)


# Configuration source that resolves secrets
class SecretsResolvingSource:
    """
    Configuration source wrapper that resolves secrets in loaded configuration.

    This can wrap any existing configuration source to add automatic secrets resolution.
    """

    def __init__(self, wrapped_source: Any) -> None:
        """
        Initialize secrets-resolving source wrapper.

        Args:
            wrapped_source: Any configuration source with load() method

        """
        self.wrapped_source = wrapped_source

    def load(self) -> dict[str, Any]:
        """Load configuration and resolve any secrets."""
        config = self.wrapped_source.load()
        return resolve_secrets(config)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to wrapped source."""
        return getattr(self.wrapped_source, name)
