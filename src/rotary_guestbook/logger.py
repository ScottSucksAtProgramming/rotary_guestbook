"""Logging configuration for the Rotary Phone Audio Guestbook system.

This module provides centralized logging configuration for the application,
setting up both console and rotating file handlers based on the application's
configuration settings.

Example:
    ```python
    from rotary_guestbook.config import ConfigManager
    from rotary_guestbook.logger import setup_logging

    config = ConfigManager("config.yaml")
    setup_logging(config)
    ```
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from rotary_guestbook.config import ConfigManager


def setup_logging(config: ConfigManager) -> None:
    """Configure the root logger with console and file handlers.

    This function sets up the root logger with both console and rotating file
    handlers based on the provided configuration. The console handler will output
    all messages, while the file handler will write to a rotating log file.

    Args:
        config: The configuration manager instance containing logging settings.

    Raises:
        OSError: If the log file cannot be created or written to.
        ValueError: If the logging configuration is invalid.
    """
    # Get logging settings from config
    log_settings = config.logging

    # Validate log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_settings.level.upper() not in valid_levels:
        raise ValueError(f"Invalid log level: {log_settings.level}")

    log_level = getattr(logging, log_settings.level.upper())
    log_format = log_settings.format
    log_file = Path(log_settings.file)
    max_bytes = log_settings.max_size
    backup_count = log_settings.backup_count

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Add rotating file handler
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
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    except OSError as e:
        root_logger.error(f"Failed to set up file logging: {e}")
        raise

    # Log the logging setup
    root_logger.info("Logging system initialized")
    root_logger.debug(
        f"Log file: {log_file}, max size: {max_bytes}, " f"backup count: {backup_count}"
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with the specified name.

    This is a convenience function to get a logger instance that will inherit
    the configuration from the root logger.

    Args:
        name: The name for the logger. If None, returns the root logger.

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
