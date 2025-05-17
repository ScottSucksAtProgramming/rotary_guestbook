"""Unit tests for the logging configuration module.

This module contains tests for the logging configuration functionality,
including setup of handlers, formatters, and log level configuration.
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rotary_guestbook.config import ConfigManager, LoggingSettings
from rotary_guestbook.logger import get_logger, setup_logging


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_config(temp_log_dir):
    """Create a mock configuration with logging settings."""
    config = MagicMock(spec=ConfigManager)
    config.logging = LoggingSettings(
        level="DEBUG",
        format="%(levelname)s - %(message)s",
        file=str(temp_log_dir / "test.log"),
        max_size=1024,
        backup_count=2,
    )
    return config


def test_setup_logging_handlers(mock_config):
    """Test that setup_logging configures handlers correctly."""
    # Setup logging
    setup_logging(mock_config)
    root_logger = logging.getLogger()

    # Check that we have both console and file handlers
    assert len(root_logger.handlers) == 2
    assert any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    assert any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in root_logger.handlers
    )


def test_setup_logging_level(mock_config):
    """Test that setup_logging sets the correct log level."""
    setup_logging(mock_config)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_setup_logging_format(mock_config):
    """Test that setup_logging uses the correct format string."""
    setup_logging(mock_config)
    root_logger = logging.getLogger()

    # Create a test log record
    record = logging.LogRecord(
        "test", logging.INFO, "test.py", 1, "Test message", (), None
    )

    # Check format for both handlers
    for handler in root_logger.handlers:
        formatted = handler.formatter.format(record)
        assert formatted.startswith("INFO - Test message")


def test_setup_logging_file_creation(mock_config, temp_log_dir):
    """Test that setup_logging creates the log file."""
    log_file = temp_log_dir / "test.log"
    assert not log_file.exists()

    setup_logging(mock_config)
    assert log_file.exists()


def test_setup_logging_file_rotation(mock_config, temp_log_dir):
    """Test that log files rotate when they reach max size."""
    log_file = temp_log_dir / "test.log"
    setup_logging(mock_config)

    # Write enough data to trigger rotation
    logger = get_logger("test")
    for _ in range(100):
        logger.info("x" * 100)

    # Check that backup files were created
    assert log_file.exists()
    assert (temp_log_dir / "test.log.1").exists()


def test_get_logger():
    """Test that get_logger returns a properly configured logger."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_setup_logging_invalid_level(mock_config):
    """Test that setup_logging raises ValueError for invalid log level."""
    mock_config.logging.level = "INVALID_LEVEL"
    with pytest.raises(ValueError):
        setup_logging(mock_config)


def test_setup_logging_file_permission_error(mock_config):
    """Test that setup_logging handles file permission errors."""
    mock_config.logging.file = "/root/test.log"  # Should be unwritable
    with pytest.raises(OSError):
        setup_logging(mock_config)


def test_setup_logging_removes_existing_handlers(mock_config):
    """Test that setup_logging removes existing handlers before adding new ones."""
    # Add some existing handlers
    root_logger = logging.getLogger()
    root_logger.addHandler(logging.StreamHandler())
    root_logger.addHandler(logging.StreamHandler())

    # Setup logging
    setup_logging(mock_config)

    # Should have exactly 2 handlers (console and file)
    assert len(root_logger.handlers) == 2
