"""Configuration management for the Rotary Phone Audio Guestbook system.

This module provides a robust configuration management system using Pydantic models
for type validation and easy access to configuration values. It handles loading
configuration from YAML files, validating the configuration structure, and providing
type-safe access to configuration values.

The configuration is organized into logical sections:
- Audio settings (devices, format, recording parameters)
- Hardware settings (GPIO pins, debounce times)
- Web interface settings (host, port, security)
- Logging settings (levels, format, file handling)
- System settings (health checks, archiving)

Example:
    ```python
    config_manager = ConfigManager("config.yaml")
    audio_settings = config_manager.audio
    print(f"Sample rate: {audio_settings.sample_rate}")
    ```
"""

import os
import warnings
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from ruamel.yaml import YAML

from rotary_guestbook.errors import ConfigError


class RecordingSettings(BaseModel):
    """Settings related to audio recording parameters."""

    input_device_index: Optional[int] = None  # PyAudio device index
    channels: int = Field(default=1, ge=1, le=2)
    rate: int = Field(default=44100, ge=8000, le=192000)
    sample_width: int = Field(
        default=2, ge=1, le=4
    )  # Bytes per sample (e.g., 2 for 16-bit)
    chunk_size: int = Field(default=1024, ge=256, le=8192)
    # Removed format from here as it's more global or tied to PyAudio format getter
    max_duration_seconds: int = Field(
        default=180, ge=10, le=600
    )  # Max recording length
    # Silence detection parameters could also go here if complex enough


class ConversionSettings(BaseModel):
    """Settings related to audio file conversion, e.g., to MP3."""

    mp3_bitrate: str = "192k"
    # Example: ["-ac", "1"] for mono, ["-q:a", "5"] for VBR quality
    ffmpeg_parameters: Optional[List[str]] = None


class AudioSettings(BaseModel):
    """Audio configuration settings.

    Defines audio-related parameters like devices, recording, and formats.
    """

    output_device_index: Optional[int] = None
    greeting_message_path: Optional[str] = None
    min_recording_time: int = Field(default=3, ge=1, le=60)
    silence_threshold: float = Field(default=0.01, ge=0.0, le=1.0)
    silence_duration: int = Field(default=2, ge=1, le=10)
    output_directory: str = "recordings"
    recording: RecordingSettings = Field(default_factory=RecordingSettings)
    conversion: ConversionSettings = Field(default_factory=ConversionSettings)

    @field_validator("output_directory")
    @classmethod
    def validate_output_directory(cls, v: str) -> str:
        """Ensure output_directory is a non-empty relative path."""
        if not isinstance(v, str) or not v:
            raise ValueError("output_directory must be a non-empty string")
        if os.path.isabs(v):
            raise ValueError("output_directory must be a relative path")
        return v


class HardwareSettings(BaseModel):
    """Hardware configuration settings.

    This model defines all hardware-related configuration parameters including
    GPIO pin assignments and debounce settings.

    Attributes:
        hook_switch_pin: GPIO pin number for the hook switch
        rotary_pulse_pin: GPIO pin number for rotary dial pulses
        rotary_dial_pin: GPIO pin number for rotary dial
        hook_switch_debounce: Debounce time for hook switch in milliseconds
        rotary_pulse_debounce: Debounce time for rotary pulses in milliseconds
    """

    hook_switch_pin: int = Field(default=17, ge=0, le=27)
    rotary_pulse_pin: int = Field(default=27, ge=0, le=27)
    rotary_dial_pin: int = Field(default=22, ge=0, le=27)
    hook_switch_debounce: int = Field(default=50, ge=0, le=1000)
    rotary_pulse_debounce: int = Field(default=10, ge=0, le=1000)


class WebSettings(BaseModel):
    """Web interface configuration settings.

    This model defines all web interface-related configuration parameters including
    server settings and security options.

    Attributes:
        host: Host address to bind the web server
        port: Port number for the web server
        debug: Whether to run in debug mode
        secret_key: Secret key for session management
        auth_enabled: Whether authentication is enabled
        auth_username: Username for authentication
        auth_password: Password for authentication
    """

    host: str = "0.0.0.0"
    port: int = Field(default=5000, ge=1024, le=65535)
    debug: bool = False
    secret_key: str = "change_this_in_production"
    auth_enabled: bool = True
    auth_username: str = "admin"
    auth_password: str = "change_this_in_production"


class LoggingSettings(BaseModel):
    """Logging configuration settings.

    This model defines all logging-related configuration parameters including
    log levels, format, and file handling.

    Attributes:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format string
        file: Log file path
        max_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
    """

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "guestbook.log"
    max_size: int = Field(default=10485760, ge=1024)  # 10MB
    backup_count: int = Field(default=5, ge=1)

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate the logging level.

        Args:
            v: The level string to validate

        Returns:
            The validated level string

        Raises:
            ValueError: If the level is not supported
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Unsupported logging level: {v}")
        return v.upper()


class SystemSettings(BaseModel):
    """System configuration settings.

    This model defines all system-related configuration parameters including
    health check settings and archiving options.

    Attributes:
        health_check_interval: Interval between health checks in seconds
        disk_space_threshold: Disk space usage threshold percentage
        cpu_usage_threshold: CPU usage threshold percentage
        memory_usage_threshold: Memory usage threshold percentage
        archive_enabled: Whether automatic archiving is enabled
        archive_interval: Interval between archives in seconds
        archive_keep_local: Whether to keep local copies after archiving
        archive_backup_location: Location for archived files
    """

    health_check_interval: int = Field(default=300, ge=60)
    disk_space_threshold: int = Field(default=90, ge=50, le=100)
    cpu_usage_threshold: int = Field(default=80, ge=50, le=100)
    memory_usage_threshold: int = Field(default=80, ge=50, le=100)
    archive_enabled: bool = True
    archive_interval: int = Field(default=86400, ge=3600)  # 24 hours
    archive_keep_local: bool = True
    archive_backup_location: str = "backups"


class Config(BaseModel):
    """Root configuration model.

    This model combines all configuration sections into a single configuration
    object with proper validation and type checking.

    Attributes:
        audio: Audio configuration settings
        hardware: Hardware configuration settings
        web: Web interface configuration settings
        logging: Logging configuration settings
        system: System configuration settings
    """

    audio: AudioSettings = Field(default_factory=AudioSettings)
    hardware: HardwareSettings = Field(default_factory=HardwareSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    system: SystemSettings = Field(default_factory=SystemSettings)


class ConfigManager:
    """Configuration manager for the Rotary Phone Audio Guestbook system.

    This class handles loading, validating, and accessing configuration settings
    from a YAML file. It uses Pydantic models for type validation and provides
    easy access to configuration values.

    Attributes:
        config_path: Path to the configuration file
        config: The validated configuration object
        yaml: YAML parser instance

    Note:
        The methods `get_audio_config`, `get_hardware_config`, etc., are
        deprecated. Use the respective properties (`.audio`, `.hardware`) instead.
    """

    def __init__(self, config_path: str) -> None:
        """Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file

        Raises:
            ConfigError: If the configuration file cannot be loaded or validated
        """
        self.config_path = Path(config_path)
        self.yaml = YAML()
        self.config = self._load_config()

    def _load_config(self) -> Config:
        """Load configuration from the YAML file and validate it."""
        try:
            if not self.config_path.exists():
                raise ConfigError(
                    "Configuration file not found",
                    f"File not found: {self.config_path}",
                )

            with self.config_path.open("r") as f:
                config_data = self.yaml.load(f)

            if not config_data:
                raise ConfigError(
                    "Empty configuration file",
                    f"File is empty: {self.config_path}",
                )

            return Config(**config_data)

        except Exception as e:
            raise ConfigError(
                "Failed to load configuration",
                f"Error loading {self.config_path}: {str(e)}",
            )

    def save_config(self) -> None:
        """Save the current configuration back to the YAML file."""
        try:
            config_dict = self.config.model_dump()
            with self.config_path.open("w") as f:
                self.yaml.dump(config_dict, f)
        except Exception as e:
            raise ConfigError(
                "Failed to save configuration",
                f"Error saving to {self.config_path}: {str(e)}",
            )

    @property
    def audio(self) -> AudioSettings:
        """Get the audio configuration settings."""
        return self.config.audio

    # Adding get_audio_config for compatibility with existing audio.py,
    # but mark as deprecated
    def get_audio_config(self) -> AudioSettings:
        """Return the audio configuration settings (DEPRECATED: use .audio property)."""
        message = (
            "ConfigManager.get_audio_config() is deprecated. "
            "Use .audio property instead."
        )
        warnings.warn(
            message,
            DeprecationWarning,
            stacklevel=2,
        )
        return self.config.audio

    @property
    def hardware(self) -> HardwareSettings:
        """Get the hardware configuration settings."""
        return self.config.hardware

    @property
    def web(self) -> WebSettings:
        """Get the web interface configuration settings."""
        return self.config.web

    @property
    def logging(self) -> LoggingSettings:
        """Get the logging configuration settings."""
        return self.config.logging

    @property
    def system(self) -> SystemSettings:
        """Get the system configuration settings."""
        return self.config.system
