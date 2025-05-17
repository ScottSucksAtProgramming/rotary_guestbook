"""Unit tests for the logging configuration module.

This module contains tests for the logging setup functionality, including handler
configuration, log level validation, and file rotation.
"""

import logging
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from rotary_guestbook.config import ConfigManager
from rotary_guestbook.logger import get_logger, setup_logging


@pytest.fixture(autouse=True)
def cleanup_logging_handlers() -> Generator[None, None, None]:
    """Ensure logging is enabled, and close handlers after each test."""
    # Cache the current global disable level
    original_disable_level = logging.root.manager.disable
    # Ensure all logging levels are enabled for the duration of the test
    logging.disable(logging.NOTSET)

    yield  # Run the test

    # Shutdown all logging handlers (flushes and closes them)
    logging.shutdown()
    # Restore the original global disable level
    logging.disable(original_disable_level)


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for log files.

    Yields:
        Path to the temporary directory.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config(temp_log_dir: Path) -> ConfigManager:
    """Create a mock configuration with logging settings.

    Args:
        temp_log_dir: Path to the temporary directory for log files.

    Returns:
        A ConfigManager instance with test logging settings.
    """
    config = ConfigManager("config.yaml")
    config.config.logging.level = "DEBUG"
    config.config.logging.format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    config.config.logging.file = str(temp_log_dir / "test.log")
    config.config.logging.max_size = 1024
    config.config.logging.backup_count = 3
    return config


def test_setup_logging_handlers(mock_config: ConfigManager) -> None:
    """Test that logging setup configures both console and file handlers."""
    setup_logging(mock_config)
    root_logger = logging.getLogger()
    handlers = root_logger.handlers

    assert len(handlers) == 2
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)
    assert any(isinstance(h, logging.handlers.RotatingFileHandler) for h in handlers)


def test_setup_logging_level(mock_config: ConfigManager) -> None:
    """Test that log level is set correctly."""
    setup_logging(mock_config)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_setup_logging_format(mock_config: ConfigManager) -> None:
    """Test that log format is set correctly."""
    setup_logging(mock_config)
    root_logger = logging.getLogger()
    formatter = root_logger.handlers[0].formatter
    assert formatter is not None
    assert formatter._fmt == mock_config.config.logging.format


def test_setup_logging_file_creation(mock_config: ConfigManager) -> None:
    """Test that log file is created."""
    log_file = Path(mock_config.config.logging.file)
    setup_logging(mock_config)
    assert log_file.exists()


def test_setup_logging_file_rotation(mock_config: ConfigManager) -> None:
    """Test that log files rotate when they reach max size."""
    logging.disable(logging.NOTSET)  # Ensure global disable is not active
    log_file = Path(mock_config.config.logging.file)

    # Explicitly get/clean the test module's logger before setup_logging.
    # This ensures it's in a known state. Set level to DEBUG to ensure
    # messages are processed if propagation works.
    logger_instance_for_test = logging.getLogger(__name__)
    logger_instance_for_test.handlers = []
    logger_instance_for_test.propagate = True
    logger_instance_for_test.setLevel(logging.DEBUG)

    setup_logging(mock_config)  # Configures root logger

    # Get the logger again; it's the same object as logger_instance_for_test.
    # Its messages should now propagate to the root logger's handlers.
    setup_logger = get_logger(__name__)
    assert setup_logger is logger_instance_for_test

    # Write enough data to trigger rotation. Max size is 1024 bytes.
    # Each message is 100 chars + overhead.
    # 20 messages of "x" * 100 = 2000 chars, should be > 1KB.
    for i in range(20):
        setup_logger.info(f"Message {i}: {'x' * 100}")

    # Flush handlers to ensure data is written before checking files.
    # logging.shutdown() in the fixture should also do this.
    for handler in logging.getLogger().handlers:  # Root handlers
        handler.flush()
    # The specific logger setup_logger shouldn't have its own handlers.
    if hasattr(setup_logger, "handlers") and setup_logger.handlers:
        for handler in setup_logger.handlers:
            handler.flush()

    # Check that backup files were created
    backup_files = list(log_file.parent.glob("test.log.*"))
    log_exists = log_file.exists()
    log_size = log_file.stat().st_size if log_exists else "N/A"
    assert_msg = (
        f"Found {len(backup_files)} backup files in {log_file.parent}. "
        f"Log file: {log_file}, Exists: {log_exists}, Size: {log_size}"
    )
    assert len(backup_files) > 0, assert_msg


def test_get_logger() -> None:
    """Test that get_logger returns a properly configured logger."""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__


def test_setup_logging_invalid_level(mock_config: ConfigManager) -> None:
    """Test that invalid log level raises ValueError."""
    mock_config.config.logging.level = "INVALID_LEVEL"
    with pytest.raises(ValueError, match="Invalid log level"):
        setup_logging(mock_config)


def test_setup_logging_file_permission_error(mock_config: ConfigManager) -> None:
    """Test that file permission errors are handled correctly."""
    mock_config.config.logging.file = "/root/test.log"
    with pytest.raises(OSError, match="Failed to set up file logging"):
        setup_logging(mock_config)


def test_setup_logging_removes_existing_handlers(mock_config: ConfigManager) -> None:
    """Test that existing handlers are removed before adding new ones."""
    root_logger = logging.getLogger()
    original_handler = logging.StreamHandler()
    root_logger.addHandler(original_handler)

    setup_logging(mock_config)
    assert original_handler not in root_logger.handlers
