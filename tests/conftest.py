"""Shared pytest fixtures for the test suite."""

import sys
from pathlib import Path
from typing import Any, Dict, Generator, Tuple
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Mock hardware-specific modules for non-Raspberry Pi environments
gpio_mocks = [
    "RPi",
    "RPi.GPIO",
    "gpiozero",
    "gpiozero.pins",
    "gpiozero.pins.rpigpio",
]
for mod in gpio_mocks:
    sys.modules[mod] = MagicMock()


@pytest.fixture
def tmp_config_file(tmp_path: Path) -> Path:
    """Create a temporary configuration file for testing.

    Args:
        tmp_path: Pytest fixture for a temporary path.

    Returns:
        Path to the temporary configuration file.
    """
    config: Dict[str, Any] = {
        "recordings_path": str(tmp_path / "recordings"),
        "alsa_hw_mapping": "hw:0,0",
        "format": "cd",
        "file_type": "wav",
        "recording_limit": 30,
        "sample_rate": 44100,
        "channels": 1,
        "mixer_control_name": "Speaker",
        "hook_gpio": 17,
        "hook_type": "NC",
        "invert_hook": False,
        "hook_bounce_time": 0.1,
        "greeting": str(tmp_path / "greeting.wav"),
        "greeting_volume": 0.8,
        "greeting_start_delay": 0,
        "beep": str(tmp_path / "beep.wav"),
        "beep_volume": 0.8,
        "beep_start_delay": 0,
        "beep_include_in_message": True,
        "time_exceeded": str(tmp_path / "time_exceeded.wav"),
        "time_exceeded_volume": 0.8,
        "time_exceeded_length": 30,
        "record_greeting_gpio": 27,
        "record_greeting_type": "NC",
        "record_greeting_bounce_time": 0.1,
        "shutdown_gpio": 22,
    }

    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    return config_path


@pytest.fixture
def mock_subprocess() -> Generator[Tuple[MagicMock, MagicMock], None, None]:
    """Mock subprocess.run and subprocess.Popen.

    Yields:
        A tuple containing mocks for subprocess.run and subprocess.Popen.
    """
    with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
        mock_run.return_value = MagicMock(returncode=0)
        mock_popen.return_value = MagicMock(
            pid=1234,
            poll=MagicMock(return_value=None),
            wait=MagicMock(return_value=0),
        )
        yield mock_run, mock_popen


@pytest.fixture
def mock_audio_interface() -> Generator[MagicMock, None, None]:
    """Create a mock AudioInterface instance.

    Yields:
        A MagicMock instance of AudioInterface.
    """
    with patch("src.audioGuestBook.AudioInterface") as mock:
        instance = mock.return_value
        instance.play_audio = MagicMock()
        instance.start_recording = MagicMock()
        instance.stop_recording = MagicMock()
        instance.stop_playback = MagicMock()
        yield instance


@pytest.fixture
def mock_button() -> Generator[MagicMock, None, None]:
    """Create a mock gpiozero.Button instance.

    Yields:
        A MagicMock instance of Button.
    """
    with patch("src.audioGuestBook.Button") as mock:  # Adjusted path if necessary
        instance = mock.return_value
        instance.when_pressed = None
        instance.when_released = None
        yield instance


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Create a mock configuration dictionary for testing.

    Returns:
        A dictionary representing a mock configuration.
    """
    return {
        "recordings_path": "/tmp/recordings",
        "alsa_hw_mapping": "hw:0,0",
        "format": "cd",
        "file_type": "wav",
        "recording_limit": 30,
        "sample_rate": 44100,
        "channels": 1,
        "mixer_control_name": "Speaker",
        "hook_gpio": 17,
        "hook_type": "NC",
        "invert_hook": False,
        "hook_bounce_time": 0.1,
        "greeting": "/tmp/greeting.wav",
        "greeting_volume": 0.8,
        "greeting_start_delay": 0,
        "beep": "/tmp/beep.wav",
        "beep_volume": 0.8,
        "beep_start_delay": 0,
        "beep_include_in_message": True,
        "time_exceeded": "/tmp/time_exceeded.wav",
        "time_exceeded_volume": 0.8,
        "time_exceeded_length": 30,
        "record_greeting_gpio": 27,
        "record_greeting_type": "NC",
        "record_greeting_bounce_time": 0.1,
        "shutdown_gpio": 22,
        "shutdown_button_hold_time": 2,
    }
