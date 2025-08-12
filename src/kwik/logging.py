"""
Logging package for kwik framework.

This package provides simple, powerful logging functionality using loguru
for the kwik web framework. It offers easy configuration and usage
both internally and externally.

Examples:
    Internal usage (within kwik library):
        from kwik.logging import logger
        logger.info("Application started")
        logger.debug("Processing request")
        logger.error("Database connection failed")

    External usage (user applications):
        from kwik.logging import logger, configure_logging

        # Basic usage with default settings
        logger.info("User action completed")
        logger.warning("Low disk space")

        # Custom configuration
        configure_logging(level="DEBUG", colorize=False)
        logger.debug("Debug information")

        # Environment variable configuration
        # Set KWIK_LOG_LEVEL=DEBUG before running
        logger.debug("This will show if KWIK_LOG_LEVEL is DEBUG")

    Advanced configuration:
        from kwik.logging import configure_logging

        # Custom format and file logging
        configure_logging(
            level="INFO",
            format_string="{time} | {level} | {message}",
            rotation="1 week",
            retention="1 month"
        )

"""

import os
import sys
from typing import Literal

from loguru import logger as _logger

# Valid log levels
LOG_LEVELS = Literal["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"]

# Default format similar to the original CustomFormatter
DEFAULT_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name} [{file.name}:{line}] | {message}"

# Get log level from environment or default to INFO
DEFAULT_LEVEL = os.getenv("KWIK_LOG_LEVEL", "INFO")

# Configure the logger with default settings
_logger.remove()  # Remove default handler
_logger.add(
    sys.stderr,
    format=DEFAULT_FORMAT,
    level=DEFAULT_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# Export the configured logger
logger = _logger


def configure_logging(
    level: LOG_LEVELS = "INFO",
    format_string: str | None = None,
    *,
    colorize: bool = True,
    **kwargs: object,
) -> None:
    """
    Configure the kwik logging system.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string, uses default if None
        colorize: Enable colored output
        **kwargs: Additional arguments passed to logger.add()

    """
    # Remove existing handlers
    _logger.remove()

    # Use provided format or default
    fmt = format_string or DEFAULT_FORMAT

    # Add new handler with specified configuration
    _logger.add(
        sys.stderr,
        format=fmt,
        level=level,
        colorize=colorize,
        backtrace=True,
        diagnose=True,
        **kwargs,
    )
