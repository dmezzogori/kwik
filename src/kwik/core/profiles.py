"""
Hierarchical configuration profiles system for Kwik framework.

This module provides environment-specific configuration loading with proper
inheritance and merging. Supports the pattern: base → environment → local.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from kwik.core.settings import ConfigurationSource


def detect_environment() -> str:
    """
    Detect the current environment from environment variables.

    Checks KWIK_ENV first, then APP_ENV, defaults to 'development'.

    Returns:
        Environment name (e.g., 'development', 'production', 'staging')

    """
    return os.getenv("KWIK_ENV", os.getenv("APP_ENV", "development"))


class ProfilesSettingsSource(ConfigurationSource):
    """
    Configuration source that loads hierarchical profiles.

    Loads configuration in this order:
    1. config/base.{json,yaml} - Base configuration for all environments
    2. config/{environment}.{json,yaml} - Environment-specific overrides
    3. config/local.{json,yaml} - Local development overrides (gitignored)

    Each subsequent file overrides values from the previous ones.
    """

    def __init__(
        self,
        profiles_dir: str | Path = "config",
        environment: str | None = None,
        file_extensions: list[str] | None = None,
    ) -> None:
        """
        Initialize profiles settings source.

        Args:
            profiles_dir: Directory containing profile configuration files
            environment: Override environment detection (defaults to auto-detect)
            file_extensions: List of file extensions to try (defaults to ['json', 'yaml', 'yml'])

        """
        self.profiles_dir = Path(profiles_dir)
        self.environment = environment or detect_environment()
        self.file_extensions = file_extensions or ["json", "yaml", "yml"]
        self._priority = 2  # Between environment (1) and file sources (3)

    def load(self) -> dict[str, Any]:
        """
        Load configuration from hierarchical profiles.

        Returns:
            Merged configuration dictionary with proper hierarchy

        """
        merged_config = {}

        # Load in hierarchy order: base → environment → local
        profile_names = ["base", self.environment, "local"]

        for profile_name in profile_names:
            profile_config = self._load_profile(profile_name)
            if profile_config:
                merged_config = self._deep_merge(merged_config, profile_config)

        return merged_config

    def _load_profile(self, profile_name: str) -> dict[str, Any] | None:
        """
        Load a specific profile configuration file.

        Args:
            profile_name: Name of the profile to load (e.g., 'base', 'production')

        Returns:
            Configuration dictionary or None if file doesn't exist

        """
        for extension in self.file_extensions:
            file_path = self.profiles_dir / f"{profile_name}.{extension}"

            if file_path.exists():
                return self._load_config_file(file_path)

        return None

    def _load_config_file(self, file_path: Path) -> dict[str, Any]:
        """
        Load configuration from a specific file.

        Args:
            file_path: Path to the configuration file

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If file format is unsupported
            ImportError: If required parser library is missing

        """
        with file_path.open(encoding="utf-8") as f:
            if file_path.suffix.lower() == ".json":
                return json.load(f)
            if file_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    import yaml  # noqa: PLC0415

                    return yaml.safe_load(f) or {}
                except ImportError as e:
                    msg = "PyYAML is required for YAML configuration files"
                    raise ImportError(msg) from e
            else:
                msg = f"Unsupported file format: {file_path.suffix}"
                raise ValueError(msg)

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary

        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @property
    def priority(self) -> int:
        """Profiles have medium priority (between env and file sources)."""
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        """Set the priority for this source."""
        self._priority = value

    def get_loaded_profiles(self) -> dict[str, Path | None]:
        """
        Get information about which profile files were loaded.

        Returns:
            Dictionary mapping profile names to file paths (or None if not found)

        """
        profiles = {}
        profile_names = ["base", self.environment, "local"]

        for profile_name in profile_names:
            file_path = None
            for extension in self.file_extensions:
                candidate_path = self.profiles_dir / f"{profile_name}.{extension}"
                if candidate_path.exists():
                    file_path = candidate_path
                    break
            profiles[profile_name] = file_path

        return profiles

    def __repr__(self) -> str:
        """String representation of the profiles source."""
        return (
            f"ProfilesSettingsSource("
            f"profiles_dir={self.profiles_dir}, "
            f"environment={self.environment}, "
            f"priority={self.priority})"
        )


class ProfileManager:
    """
    Manager for handling environment profiles and configuration.

    Provides utilities for working with the hierarchical configuration system.
    """

    def __init__(self, profiles_dir: str | Path = "config") -> None:
        """
        Initialize profile manager.

        Args:
            profiles_dir: Directory containing profile configuration files

        """
        self.profiles_dir = Path(profiles_dir)

    def list_available_profiles(self) -> list[str]:
        """
        List all available configuration profiles.

        Returns:
            List of profile names (without file extensions)

        """
        profiles = set()

        if not self.profiles_dir.exists():
            return []

        for file_path in self.profiles_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in [".json", ".yaml", ".yml"]:
                profile_name = file_path.stem
                if profile_name not in ["base", "local"]:  # These are special profiles
                    profiles.add(profile_name)

        return sorted(profiles)

    def validate_profile_structure(self) -> dict[str, list[str]]:
        """
        Validate the structure of configuration profiles.

        Returns:
            Dictionary with validation results:
            - 'missing': List of recommended profiles that don't exist
            - 'found': List of profiles that exist
            - 'warnings': List of potential issues

        """
        result = {"missing": [], "found": [], "warnings": []}

        # Check for base profile
        base_files = list(self.profiles_dir.glob("base.*"))
        if not base_files:
            result["missing"].append("base")
        else:
            result["found"].append("base")

        # Check for environment-specific profiles
        current_env = detect_environment()
        env_files = list(self.profiles_dir.glob(f"{current_env}.*"))
        if not env_files:
            result["missing"].append(current_env)
        else:
            result["found"].append(current_env)

        # Check for local profile
        local_files = list(self.profiles_dir.glob("local.*"))
        if local_files:
            result["found"].append("local")
            result["warnings"].append("local profile found - ensure it's in .gitignore for security")

        return result

    def create_profile_template(self, profile_name: str, format_type: str = "yaml") -> Path:
        """
        Create a template configuration file for a profile.

        Args:
            profile_name: Name of the profile to create
            format_type: File format ('yaml' or 'json')

        Returns:
            Path to the created template file

        Raises:
            ValueError: If format_type is not supported

        """
        if format_type not in ["yaml", "json"]:
            msg = f"Unsupported format: {format_type}. Use 'yaml' or 'json'"
            raise ValueError(msg)

        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        file_path = self.profiles_dir / f"{profile_name}.{format_type}"

        if format_type == "yaml":
            template_content = f"""# {profile_name.title()} Environment Configuration
# This file contains {profile_name}-specific settings for Kwik

# Example settings (remove or customize as needed)
# PROJECT_NAME: "kwik-{profile_name}"
# DEBUG: {"true" if profile_name == "development" else "false"}
# LOG_LEVEL: "{"DEBUG" if profile_name == "development" else "INFO"}"

# Database settings
# POSTGRES_SERVER: "localhost"
# POSTGRES_DB: "kwik_{profile_name}"

# Add your {profile_name}-specific configuration here
"""
        else:  # JSON
            template_content = f"""{{
  "_comment": "{profile_name.title()} Environment Configuration",
  "_description": "This file contains {profile_name}-specific settings for Kwik",

  "PROJECT_NAME": "kwik-{profile_name}",
  "DEBUG": {"true" if profile_name == "development" else "false"},
  "LOG_LEVEL": "{"DEBUG" if profile_name == "development" else "INFO"}",

  "_database": "Database settings section",
  "POSTGRES_SERVER": "localhost",
  "POSTGRES_DB": "kwik_{profile_name}"
}}
"""

        file_path.write_text(template_content, encoding="utf-8")
        return file_path
