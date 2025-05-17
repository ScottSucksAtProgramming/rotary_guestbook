"""Unit tests for the configuration management system.

This module contains comprehensive tests for the configuration management system,
including tests for the ConfigManager class and all Pydantic models used for
configuration validation.

The test suite covers:
- Loading valid and invalid configuration files
- Default value handling
- Configuration validation
- Property access
- Configuration saving
- Error handling

Example:
    ```python
    # Running a specific test
    pytest tests/unit/test_config.py::test_load_valid_config -v

    # Running all config tests
    pytest tests/unit/test_config.py -v
    ```
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from rotary_guestbook.config import (
    AudioSettings,
    Config,
    ConfigManager,
    HardwareSettings,
    LoggingSettings,
    SystemSettings,
    WebSettings,
)
from rotary_guestbook.errors import ConfigError


@pytest.fixture
def valid_config_data() -> Dict[str, Any]:
    """Create a valid configuration data dictionary.

    Returns:
        A dictionary containing valid configuration data for testing
    """
    return {
        "audio": {
            "input_device": "default",
            "output_device": "default",
            "sample_rate": 44100,
            "channels": 2,
            "chunk_size": 1024,
            "format": "int16",
            "max_recording_time": 300,
            "min_recording_time": 3,
            "silence_threshold": 0.01,
            "silence_duration": 2,
            "recording_format": "mp3",
            "bitrate": "128k",
            "output_directory": "recordings",
        },
        "hardware": {
            "hook_switch_pin": 17,
            "rotary_pulse_pin": 27,
            "rotary_dial_pin": 22,
            "hook_switch_debounce": 50,
            "rotary_pulse_debounce": 10,
        },
        "web": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False,
            "secret_key": "test_key",
            "auth_enabled": True,
            "auth_username": "admin",
            "auth_password": "password",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file": "test.log",
            "max_size": 10485760,
            "backup_count": 5,
        },
        "system": {
            "health_check_interval": 300,
            "disk_space_threshold": 90,
            "cpu_usage_threshold": 80,
            "memory_usage_threshold": 80,
            "archive_enabled": True,
            "archive_interval": 86400,
            "archive_keep_local": True,
            "archive_backup_location": "backups",
        },
    }


@pytest.fixture
def config_file(tmp_path: Path, valid_config_data: Dict[str, Any]) -> Path:
    """Create a temporary configuration file with valid data.

    Args:
        tmp_path: Pytest fixture providing a temporary directory
        valid_config_data: Fixture providing valid configuration data

    Returns:
        Path to the temporary configuration file
    """
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        import yaml

        yaml.dump(valid_config_data, f)
    return config_path


def test_load_valid_config(config_file: Path) -> None:
    """Test loading a valid configuration file.

    Args:
        config_file: Path to a temporary configuration file with valid data
    """
    config_manager = ConfigManager(str(config_file))
    assert config_manager.audio.sample_rate == 44100
    assert config_manager.hardware.hook_switch_pin == 17
    assert config_manager.web.port == 5000
    assert config_manager.logging.level == "INFO"
    assert config_manager.system.health_check_interval == 300


def test_load_nonexistent_config(tmp_path: Path) -> None:
    """Test loading a non-existent configuration file.

    Args:
        tmp_path: Pytest fixture providing a temporary directory
    """
    with pytest.raises(ConfigError) as exc_info:
        ConfigManager(str(tmp_path / "nonexistent.yaml"))
    assert "Configuration file not found" in str(exc_info.value)


def test_load_empty_config(tmp_path: Path) -> None:
    """Test loading an empty configuration file.

    Args:
        tmp_path: Pytest fixture providing a temporary directory
    """
    config_path = tmp_path / "empty.yaml"
    config_path.touch()
    with pytest.raises(ConfigError) as exc_info:
        ConfigManager(str(config_path))
    assert "Empty configuration file" in str(exc_info.value)


def test_load_invalid_config(tmp_path: Path) -> None:
    """Test loading an invalid configuration file.

    Args:
        tmp_path: Pytest fixture providing a temporary directory
    """
    config_path = tmp_path / "invalid.yaml"
    with open(config_path, "w") as f:
        f.write("invalid: yaml: content: [")
    with pytest.raises(ConfigError) as exc_info:
        ConfigManager(str(config_path))
    assert "Failed to load configuration" in str(exc_info.value)


def test_default_values() -> None:
    """Test that default values are used when not specified in config."""
    config = Config()
    assert config.audio.sample_rate == 44100
    assert config.audio.channels == 1
    assert config.hardware.hook_switch_pin == 17
    assert config.web.port == 5000
    assert config.logging.level == "INFO"
    assert config.system.health_check_interval == 300


def test_audio_settings_validation() -> None:
    """Test validation of audio settings."""
    # Test invalid sample rate
    with pytest.raises(ValueError) as exc_info:
        AudioSettings(sample_rate=1000)  # Below minimum
    assert "sample_rate" in str(exc_info.value)

    # Test invalid channels
    with pytest.raises(ValueError) as exc_info:
        AudioSettings(channels=3)  # Above maximum
    assert "channels" in str(exc_info.value)

    # Test invalid format
    with pytest.raises(ValueError) as exc_info:
        AudioSettings(format="invalid")
    assert "Unsupported audio format" in str(exc_info.value)

    # Test invalid recording format
    with pytest.raises(ValueError) as exc_info:
        AudioSettings(recording_format="invalid")
    assert "Unsupported recording format" in str(exc_info.value)


def test_hardware_settings_validation() -> None:
    """Test validation of hardware settings."""
    # Test invalid GPIO pin
    with pytest.raises(ValueError) as exc_info:
        HardwareSettings(hook_switch_pin=28)  # Above maximum
    assert "hook_switch_pin" in str(exc_info.value)

    # Test invalid debounce time
    with pytest.raises(ValueError) as exc_info:
        HardwareSettings(hook_switch_debounce=2000)  # Above maximum
    assert "hook_switch_debounce" in str(exc_info.value)


def test_web_settings_validation() -> None:
    """Test validation of web settings."""
    # Test invalid port
    with pytest.raises(ValueError) as exc_info:
        WebSettings(port=80)  # Below minimum
    assert "port" in str(exc_info.value)

    # Test invalid port
    with pytest.raises(ValueError) as exc_info:
        WebSettings(port=70000)  # Above maximum
    assert "port" in str(exc_info.value)


def test_logging_settings_validation() -> None:
    """Test validation of logging settings."""
    # Test invalid level
    with pytest.raises(ValueError) as exc_info:
        LoggingSettings(level="INVALID")
    assert "Unsupported logging level" in str(exc_info.value)

    # Test invalid max size
    with pytest.raises(ValueError) as exc_info:
        LoggingSettings(max_size=512)  # Below minimum
    assert "max_size" in str(exc_info.value)

    # Test invalid backup count
    with pytest.raises(ValueError) as exc_info:
        LoggingSettings(backup_count=0)  # Below minimum
    assert "backup_count" in str(exc_info.value)


def test_system_settings_validation() -> None:
    """Test validation of system settings."""
    # Test invalid health check interval
    with pytest.raises(ValueError) as exc_info:
        SystemSettings(health_check_interval=30)  # Below minimum
    assert "health_check_interval" in str(exc_info.value)

    # Test invalid disk space threshold
    with pytest.raises(ValueError) as exc_info:
        SystemSettings(disk_space_threshold=40)  # Below minimum
    assert "disk_space_threshold" in str(exc_info.value)

    # Test invalid archive interval
    with pytest.raises(ValueError) as exc_info:
        SystemSettings(archive_interval=1800)  # Below minimum
    assert "archive_interval" in str(exc_info.value)


def test_save_config(config_file: Path) -> None:
    """Test saving configuration to a file.

    Args:
        config_file: Path to a temporary configuration file
    """
    config_manager = ConfigManager(str(config_file))
    config_manager.audio.sample_rate = 48000
    config_manager.save_config()

    # Load the saved config and verify changes
    new_config_manager = ConfigManager(str(config_file))
    assert new_config_manager.audio.sample_rate == 48000


def test_save_config_error(config_file: Path) -> None:
    """Test error handling when saving configuration.

    Args:
        config_file: Path to a temporary configuration file
    """
    config_manager = ConfigManager(str(config_file))
    with patch("pathlib.Path.open", side_effect=IOError("Permission denied")):
        with pytest.raises(ConfigError) as exc_info:
            config_manager.save_config()
        assert "Failed to save configuration" in str(exc_info.value)


def test_property_access(config_file: Path) -> None:
    """Test accessing configuration properties.

    Args:
        config_file: Path to a temporary configuration file
    """
    config_manager = ConfigManager(str(config_file))
    assert isinstance(config_manager.audio, AudioSettings)
    assert isinstance(config_manager.hardware, HardwareSettings)
    assert isinstance(config_manager.web, WebSettings)
    assert isinstance(config_manager.logging, LoggingSettings)
    assert isinstance(config_manager.system, SystemSettings)
