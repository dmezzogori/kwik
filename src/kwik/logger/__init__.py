"""
Logging package for kwik framework.

This package provides custom logging functionality including formatters
and configuration for the kwik web framework.
"""

import logging
from typing import ClassVar

from kwik.core.settings import get_settings


class CustomFormatter(logging.Formatter):
    """Custom logging formatter with color-coded output for different log levels."""

    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s | %(levelname)s | %(name)s [%(filename)s:%(lineno)d] | %(message)s"

    FORMATS: ClassVar[dict[int, str]] = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with color based on log level."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# https://docs.python.org/3/library/logging.html
logging.basicConfig(level=get_settings().LOG_LEVEL)

uvicorn_logger = logging.getLogger("uvicorn.error")
uvicorn_logger.propagate = False

logger = logging.getLogger("kwik")

if logger.hasHandlers():
    logger.handlers.clear()


logger.propagate = False
logger.setLevel(get_settings().LOG_LEVEL)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

ch.setFormatter(CustomFormatter())

logger.addHandler(ch)
