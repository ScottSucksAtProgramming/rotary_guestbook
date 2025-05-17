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
    log_file = Path(mock_config.config.logging.file)
    setup_logger = get_logger(__name__)
    setup_logging(mock_config)

    # Write enough data to trigger rotation
    for _ in range(100):
        setup_logger.info("x" * 100)

    # Check that backup files were created
    backup_files = list(log_file.parent.glob("test.log.*"))
    assert len(backup_files) > 0


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
