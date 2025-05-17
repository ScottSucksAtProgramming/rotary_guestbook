"""Centralized logging configuration for the Rotary Phone Guestbook project.

This module provides a centralized logging setup that configures both console and file
handlers. The logging configuration is managed through the ConfigManager, allowing for
dynamic configuration of log levels, formats, and file rotation settings.

Example:
    To use the logger in a module:

    ```python
    from rotary_guestbook.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Application started")
    ```
"""

import logging
import logging.handlers
from pathlib import Path

from rotary_guestbook.config import ConfigManager


def setup_logging(config_manager: ConfigManager) -> None:
    """Configure the root logger with console and file handlers.

    Args:
        config_manager: The configuration manager instance containing logging settings.

    Raises:
        ValueError: If an invalid log level is specified in the configuration.
        OSError: If there are issues creating or accessing the log directory.
    """
    # Get logging settings from config
    log_settings = config_manager.config.logging
    log_level = log_settings.level.upper()
    log_format = log_settings.format
    log_file = Path(log_settings.file)
    max_bytes = log_settings.max_size
    backup_count = log_settings.backup_count

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_level not in valid_levels:
        raise ValueError(
            f"Invalid log level: {log_level}. Must be one of {valid_levels}"
        )

    # Get numeric log level
    numeric_level = getattr(logging, log_level)

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler
    try:
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    except OSError as e:
        raise OSError(f"Failed to set up file logging: {e}") from e

    # Set root logger level
    root_logger.setLevel(numeric_level)

    # Log initialization
    root_logger.info("Logging system initialized")
    root_logger.debug(
        "Log file: %s, max size: %d bytes, backup count: %d",
        log_file,
        max_bytes,
        backup_count,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: The name for the logger, typically __name__ of the calling module.

    Returns:
        A logger instance configured with the root logger's settings.
    """
    return logging.getLogger(name)
