"""
Hot reloading system for Kwik configuration.

This module provides safe, transactional configuration reloading with file watching
and validation hooks for application components.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from kwik.core.settings import BaseKwikSettings

logger = logging.getLogger(__name__)

# Type aliases
ReloadHook = Callable[[BaseKwikSettings, BaseKwikSettings], None]
AsyncReloadHook = Callable[[BaseKwikSettings, BaseKwikSettings], Any]  # Can return coroutine


class SettingsReloadEvent:
    """Event object passed to reload hooks with configuration change information."""

    def __init__(
        self,
        old_settings: BaseKwikSettings,
        new_settings: BaseKwikSettings,
        changed_files: set[Path],
        reload_reason: str = "file_change",
    ) -> None:
        """
        Initialize settings reload event.

        Args:
            old_settings: Previous settings instance
            new_settings: New settings instance after reload
            changed_files: Set of files that triggered the reload
            reload_reason: Reason for the reload (e.g., 'file_change', 'manual')

        """
        self.old_settings = old_settings
        self.new_settings = new_settings
        self.changed_files = changed_files
        self.reload_reason = reload_reason

    def get_changed_values(self) -> dict[str, tuple[Any, Any]]:
        """
        Get dictionary of changed configuration values.

        Returns:
            Dictionary mapping field names to (old_value, new_value) tuples

        """
        changed = {}
        old_dict = self.old_settings.model_dump()
        new_dict = self.new_settings.model_dump()

        all_keys = set(old_dict.keys()) | set(new_dict.keys())

        for key in all_keys:
            old_value = old_dict.get(key)
            new_value = new_dict.get(key)

            if old_value != new_value:
                changed[key] = (old_value, new_value)

        return changed

    def has_field_changed(self, field_name: str) -> bool:
        """Check if a specific field has changed."""
        return field_name in self.get_changed_values()


class ConfigFileWatcher(FileSystemEventHandler):
    """File system event handler for configuration file changes."""

    def __init__(self, hot_reload_manager: HotReloadManager) -> None:
        """
        Initialize config file watcher.

        Args:
            hot_reload_manager: Reference to the hot reload manager

        """
        self.hot_reload_manager = hot_reload_manager
        self.debounce_timer: threading.Timer | None = None
        self.debounce_delay = 0.5  # 500ms debounce to handle rapid file changes

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only react to configuration files
        if self.hot_reload_manager._is_watched_file(file_path):
            logger.debug(f"Configuration file changed: {file_path}")
            self._debounced_reload(file_path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events (for new config files)."""
        self.on_modified(event)  # Treat creation same as modification

    def _debounced_reload(self, file_path: Path) -> None:
        """Debounce rapid file changes to avoid multiple reloads."""
        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.debounce_timer = threading.Timer(
            self.debounce_delay, lambda: self.hot_reload_manager.trigger_reload({file_path})
        )
        self.debounce_timer.start()


class HotReloadManager:
    """
    Manager for hot reloading configuration files with validation and hooks.

    Provides safe, transactional reloading of settings with file watching and
    component notification system.
    """

    def __init__(self) -> None:
        """Initialize hot reload manager."""
        self._enabled = False
        self._observer: Observer | None = None
        self._watched_paths: set[Path] = set()
        self._watched_files: set[Path] = set()
        self._reload_hooks: list[ReloadHook] = []
        self._async_reload_hooks: list[AsyncReloadHook] = []
        self._current_settings: BaseKwikSettings | None = None
        self._settings_factory = None  # Will be set by configure method
        self._lock = threading.Lock()

    def configure(
        self,
        settings_factory,
        watched_paths: list[str | Path] | None = None,
        watched_files: list[str | Path] | None = None,
    ) -> None:
        """
        Configure the hot reload manager.

        Args:
            settings_factory: Factory instance for creating settings
            watched_paths: Directories to watch for changes
            watched_files: Specific files to watch for changes

        """
        self._settings_factory = settings_factory

        if watched_paths:
            self._watched_paths = {Path(p) for p in watched_paths}

        if watched_files:
            self._watched_files = {Path(f) for f in watched_files}

    def enable(self) -> None:
        """Enable hot reloading with file watching."""
        if self._enabled:
            logger.warning("Hot reload is already enabled")
            return

        if not self._settings_factory:
            msg = "Hot reload manager must be configured before enabling"
            raise RuntimeError(msg)

        self._current_settings = self._settings_factory.get_settings()

        # Set up file watching
        self._observer = Observer()
        watcher = ConfigFileWatcher(self)

        # Watch specified paths
        for path in self._watched_paths:
            if path.exists():
                self._observer.schedule(watcher, str(path), recursive=True)
                logger.info(f"Watching directory for config changes: {path}")

        # Watch specific files (watch their parent directories)
        for file_path in self._watched_files:
            if file_path.exists():
                parent_dir = file_path.parent
                if parent_dir not in self._watched_paths:
                    self._observer.schedule(watcher, str(parent_dir), recursive=False)
                    logger.info(f"Watching file for config changes: {file_path}")

        self._observer.start()
        self._enabled = True
        logger.info("Hot reload enabled")

    def disable(self) -> None:
        """Disable hot reloading and stop file watching."""
        if not self._enabled:
            return

        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        self._enabled = False
        logger.info("Hot reload disabled")

    def add_reload_hook(self, hook: ReloadHook) -> None:
        """
        Add a synchronous hook to be called when settings are reloaded.

        Args:
            hook: Function that takes (old_settings, new_settings) arguments

        """
        self._reload_hooks.append(hook)

    def add_async_reload_hook(self, hook: AsyncReloadHook) -> None:
        """
        Add an asynchronous hook to be called when settings are reloaded.

        Args:
            hook: Async function that takes (old_settings, new_settings) arguments

        """
        self._async_reload_hooks.append(hook)

    def remove_reload_hook(self, hook: ReloadHook) -> None:
        """Remove a synchronous reload hook."""
        if hook in self._reload_hooks:
            self._reload_hooks.remove(hook)

    def remove_async_reload_hook(self, hook: AsyncReloadHook) -> None:
        """Remove an asynchronous reload hook."""
        if hook in self._async_reload_hooks:
            self._async_reload_hooks.remove(hook)

    def trigger_reload(self, changed_files: set[Path] | None = None) -> bool:
        """
        Manually trigger a configuration reload.

        Args:
            changed_files: Set of files that changed (for hook notification)

        Returns:
            True if reload was successful, False otherwise

        """
        with self._lock:
            if not self._enabled or not self._settings_factory:
                logger.warning("Cannot reload: hot reload not enabled or not configured")
                return False

            changed_files = changed_files or set()

            try:
                # Create new settings instance
                old_settings = self._current_settings
                new_settings = self._settings_factory.get_settings()

                # Validate new settings by accessing a property
                _ = new_settings.PROJECT_NAME  # This will trigger validation

                # If we get here, validation succeeded
                self._current_settings = new_settings

                # Create reload event
                reload_event = SettingsReloadEvent(
                    old_settings=old_settings,
                    new_settings=new_settings,
                    changed_files=changed_files,
                    reload_reason="file_change" if changed_files else "manual",
                )

                # Call synchronous hooks
                self._call_sync_hooks(reload_event)

                # Schedule async hooks if we're in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    if self._async_reload_hooks:
                        loop.create_task(self._call_async_hooks(reload_event))
                except RuntimeError:
                    # No event loop running, skip async hooks
                    if self._async_reload_hooks:
                        logger.warning("Async reload hooks skipped (no event loop)")

                logger.info(f"Configuration reloaded successfully. Changed files: {changed_files}")
                return True

            except Exception as e:
                logger.exception(f"Configuration reload failed: {e}")
                return False

    def _call_sync_hooks(self, reload_event: SettingsReloadEvent) -> None:
        """Call all synchronous reload hooks."""
        for hook in self._reload_hooks:
            try:
                hook(reload_event.old_settings, reload_event.new_settings)
                logger.debug(f"Called reload hook: {hook.__name__}")
            except Exception as e:
                logger.exception(f"Error in reload hook {hook.__name__}: {e}")

    async def _call_async_hooks(self, reload_event: SettingsReloadEvent) -> None:
        """Call all asynchronous reload hooks."""
        for hook in self._async_reload_hooks:
            try:
                result = hook(reload_event.old_settings, reload_event.new_settings)
                if asyncio.iscoroutine(result):
                    await result
                logger.debug(f"Called async reload hook: {hook.__name__}")
            except Exception as e:
                logger.exception(f"Error in async reload hook {hook.__name__}: {e}")

    def _is_watched_file(self, file_path: Path) -> bool:
        """Check if a file is being watched for changes."""
        # Check if it's in the explicitly watched files
        if file_path in self._watched_files:
            return True

        # Check if it's a config file in a watched directory
        if file_path.suffix.lower() in [".json", ".yaml", ".yml", ".env"]:
            return any(
                file_path.is_relative_to(watched_path) or file_path.parent == watched_path
                for watched_path in self._watched_paths
            )

        return False

    @property
    def enabled(self) -> bool:
        """Check if hot reloading is enabled."""
        return self._enabled

    @property
    def current_settings(self) -> BaseKwikSettings | None:
        """Get the current settings instance."""
        return self._current_settings


# Global hot reload manager instance
_hot_reload_manager = HotReloadManager()


def configure_hot_reload(
    settings_factory,
    watched_paths: list[str | Path] | None = None,
    watched_files: list[str | Path] | None = None,
) -> None:
    """
    Configure the global hot reload manager.

    Args:
        settings_factory: Factory instance for creating settings
        watched_paths: Directories to watch for changes
        watched_files: Specific files to watch for changes

    """
    _hot_reload_manager.configure(
        settings_factory=settings_factory,
        watched_paths=watched_paths,
        watched_files=watched_files,
    )


def enable_hot_reload() -> None:
    """Enable hot reloading for the global manager."""
    _hot_reload_manager.enable()


def disable_hot_reload() -> None:
    """Disable hot reloading for the global manager."""
    _hot_reload_manager.disable()


def trigger_reload(changed_files: set[Path] | None = None) -> bool:
    """
    Manually trigger a configuration reload.

    Args:
        changed_files: Set of files that changed

    Returns:
        True if reload was successful, False otherwise

    """
    return _hot_reload_manager.trigger_reload(changed_files)


def add_reload_hook(hook: ReloadHook) -> None:
    """
    Add a hook to be called when settings are reloaded.

    Args:
        hook: Function that takes (old_settings, new_settings) arguments

    """
    _hot_reload_manager.add_reload_hook(hook)


def add_async_reload_hook(hook: AsyncReloadHook) -> None:
    """
    Add an async hook to be called when settings are reloaded.

    Args:
        hook: Async function that takes (old_settings, new_settings) arguments

    """
    _hot_reload_manager.add_async_reload_hook(hook)


def remove_reload_hook(hook: ReloadHook) -> None:
    """Remove a reload hook."""
    _hot_reload_manager.remove_reload_hook(hook)


def remove_async_reload_hook(hook: AsyncReloadHook) -> None:
    """Remove an async reload hook."""
    _hot_reload_manager.remove_async_reload_hook(hook)


def on_settings_reload(func: ReloadHook) -> ReloadHook:
    """
    Decorator to automatically register a function as a settings reload hook.

    Usage:
        @on_settings_reload
        def refresh_database_pool(old_settings, new_settings):
            if old_settings.DB_HOST != new_settings.DB_HOST:
                recreate_pool()
    """
    add_reload_hook(func)
    return func


def on_settings_reload_async(func: AsyncReloadHook) -> AsyncReloadHook:
    """
    Decorator to automatically register an async function as a settings reload hook.

    Usage:
        @on_settings_reload_async
        async def refresh_cache(old_settings, new_settings):
            await cache.flush()
    """
    add_async_reload_hook(func)
    return func


def get_hot_reload_manager() -> HotReloadManager:
    """Get the global hot reload manager instance."""
    return _hot_reload_manager
