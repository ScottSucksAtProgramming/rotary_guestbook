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
    ConversionSettings,
    HardwareSettings,
    LoggingSettings,
    RecordingSettings,
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
            "output_device_index": None,  # Or some valid index
            "greeting_message_path": "path/to/greeting.wav",
            "min_recording_time": 3,
            "silence_threshold": 0.01,
            "silence_duration": 2,
            "output_directory": "recordings",
            "recording": {
                "input_device_index": None,  # Or some valid index
                "rate": 44100,
                "channels": 2,
                "sample_width": 2,
                "chunk_size": 1024,
                "max_duration_seconds": 300,
            },
            "conversion": {
                "mp3_bitrate": "128k",
                "ffmpeg_parameters": None,
            },
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
    assert config_manager.audio.recording.rate == 44100
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
    assert config.audio.recording.rate == 44100
    assert config.audio.recording.channels == 1
    assert config.hardware.hook_switch_pin == 17
    assert config.web.port == 5000
    assert config.logging.level == "INFO"
    assert config.system.health_check_interval == 300


def test_audio_settings_validation() -> None:
    """Test validation of audio settings."""
    # Test invalid output_directory
    with pytest.raises(ValueError) as exc_info:
        AudioSettings(output_directory="/abs/path/recordings")
    assert "output_directory must be a relative path" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        AudioSettings(output_directory="")
    assert "output_directory must be a non-empty string" in str(exc_info.value)
    # Valid case
    assert AudioSettings(output_directory="rec").output_directory == "rec"

    # Test min_recording_time boundaries (ge=1, le=60)
    with pytest.raises(ValueError):
        AudioSettings(min_recording_time=0)
    with pytest.raises(ValueError):
        AudioSettings(min_recording_time=61)
    assert AudioSettings(min_recording_time=1).min_recording_time == 1
    assert AudioSettings(min_recording_time=60).min_recording_time == 60

    # Test silence_threshold boundaries (ge=0.0, le=1.0)
    with pytest.raises(ValueError):
        AudioSettings(silence_threshold=-0.1)
    with pytest.raises(ValueError):
        AudioSettings(silence_threshold=1.1)
    assert AudioSettings(silence_threshold=0.0).silence_threshold == 0.0
    assert AudioSettings(silence_threshold=1.0).silence_threshold == 1.0

    # Test silence_duration boundaries (ge=1, le=10)
    with pytest.raises(ValueError):
        AudioSettings(silence_duration=0)
    with pytest.raises(ValueError):
        AudioSettings(silence_duration=11)
    assert AudioSettings(silence_duration=1).silence_duration == 1
    assert AudioSettings(silence_duration=10).silence_duration == 10

    # Test that default RecordingSettings and ConversionSettings are valid
    assert AudioSettings().recording is not None
    assert AudioSettings().conversion is not None


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
    assert SystemSettings(health_check_interval=60).health_check_interval == 60

    # Test invalid disk space threshold
    with pytest.raises(ValueError) as exc_info:
        SystemSettings(disk_space_threshold=40)  # Below minimum
    assert "disk_space_threshold" in str(exc_info.value)
    with pytest.raises(ValueError):
        SystemSettings(disk_space_threshold=101)  # Above maximum
    assert SystemSettings(disk_space_threshold=50).disk_space_threshold == 50
    assert SystemSettings(disk_space_threshold=100).disk_space_threshold == 100

    # Test cpu_usage_threshold boundaries (ge=50, le=100)
    with pytest.raises(ValueError):
        SystemSettings(cpu_usage_threshold=49)
    with pytest.raises(ValueError):
        SystemSettings(cpu_usage_threshold=101)
    assert SystemSettings(cpu_usage_threshold=50).cpu_usage_threshold == 50
    assert SystemSettings(cpu_usage_threshold=100).cpu_usage_threshold == 100

    # Test memory_usage_threshold boundaries (ge=50, le=100)
    with pytest.raises(ValueError):
        SystemSettings(memory_usage_threshold=49)
    with pytest.raises(ValueError):
        SystemSettings(memory_usage_threshold=101)
    assert SystemSettings(memory_usage_threshold=50).memory_usage_threshold == 50
    assert SystemSettings(memory_usage_threshold=100).memory_usage_threshold == 100

    # Test invalid archive interval
    with pytest.raises(ValueError) as exc_info:
        SystemSettings(archive_interval=1800)  # Below minimum
    assert "archive_interval" in str(exc_info.value)
    assert SystemSettings(archive_interval=3600).archive_interval == 3600


def test_save_config(config_file: Path) -> None:
    """Test saving configuration to a file.

    Args:
        config_file: Path to a temporary configuration file
    """
    config_manager = ConfigManager(str(config_file))
    config_manager.audio.recording.rate = 48000
    config_manager.save_config()

    reloaded_config_manager = ConfigManager(str(config_file))
    assert reloaded_config_manager.audio.recording.rate == 48000


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


def test_recording_settings_validation() -> None:
    """Test validation of recording settings."""
    # rate: ge=8000, le=192000
    with pytest.raises(ValueError):
        RecordingSettings(rate=7999)
    with pytest.raises(ValueError):
        RecordingSettings(rate=192001)
    assert RecordingSettings(rate=8000).rate == 8000
    assert RecordingSettings(rate=192000).rate == 192000

    # channels: ge=1, le=2
    with pytest.raises(ValueError):
        RecordingSettings(channels=0)
    with pytest.raises(ValueError):
        RecordingSettings(channels=3)
    assert RecordingSettings(channels=1).channels == 1
    assert RecordingSettings(channels=2).channels == 2

    # sample_width: ge=1, le=4
    with pytest.raises(ValueError):
        RecordingSettings(sample_width=0)
    with pytest.raises(ValueError):
        RecordingSettings(sample_width=5)
    assert RecordingSettings(sample_width=1).sample_width == 1
    assert RecordingSettings(sample_width=4).sample_width == 4

    # chunk_size: ge=256, le=8192
    with pytest.raises(ValueError):
        RecordingSettings(chunk_size=255)
    with pytest.raises(ValueError):
        RecordingSettings(chunk_size=8193)
    assert RecordingSettings(chunk_size=256).chunk_size == 256
    assert RecordingSettings(chunk_size=8192).chunk_size == 8192

    # max_duration_seconds: ge=10, le=600
    with pytest.raises(ValueError):
        RecordingSettings(max_duration_seconds=9)
    with pytest.raises(ValueError):
        RecordingSettings(max_duration_seconds=601)
    assert RecordingSettings(max_duration_seconds=10).max_duration_seconds == 10
    assert RecordingSettings(max_duration_seconds=600).max_duration_seconds == 600

    # input_device_index is Optional[int], Pydantic handles type. Valid examples:
    assert RecordingSettings(input_device_index=None).input_device_index is None
    assert RecordingSettings(input_device_index=1).input_device_index == 1


def test_conversion_settings_validation() -> None:
    """Test validation of conversion settings."""
    # mp3_bitrate: str
    assert ConversionSettings(mp3_bitrate="128k").mp3_bitrate == "128k"
    with pytest.raises(ValueError):  # Pydantic's ValidationError
        ConversionSettings(mp3_bitrate=128)

    # ffmpeg_parameters: Optional[List[str]]
    assert ConversionSettings(ffmpeg_parameters=None).ffmpeg_parameters is None
    assert ConversionSettings(ffmpeg_parameters=["-ac", "1"]).ffmpeg_parameters == [
        "-ac",
        "1",
    ]
    with pytest.raises(ValueError):
        ConversionSettings(ffmpeg_parameters="not a list")
    with pytest.raises(ValueError):
        ConversionSettings(ffmpeg_parameters=[1, 2, 3])


def test_get_audio_config_deprecated(config_file: Path) -> None:
    """Test that get_audio_config issues a DeprecationWarning."""
    config_manager = ConfigManager(str(config_file))
    with pytest.warns(
        DeprecationWarning,
        match="ConfigManager.get_audio_config\\(\\) is deprecated. "
        "Use .audio property instead.",
    ):
        audio_settings = config_manager.get_audio_config()
        assert isinstance(
            audio_settings, AudioSettings
        )  # Also check it returns the right thing
