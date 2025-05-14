import threading
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.audioGuestBook import AudioGuestBook, CurrentEvent


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
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
        "greeting": "/path/to/greeting.wav",
        "greeting_volume": 0.8,
        "greeting_start_delay": 0,
        "beep": "/path/to/beep.wav",
        "beep_volume": 0.8,
        "beep_start_delay": 0,
        "beep_include_in_message": True,
        "time_exceeded": "/path/to/time_exceeded.wav",
        "time_exceeded_volume": 0.8,
        "time_exceeded_length": 30,
        "record_greeting_gpio": 27,
        "record_greeting_type": "NC",
        "record_greeting_bounce_time": 0.1,
        "shutdown_gpio": 22,
        "shutdown_button_hold_time": 2,
    }  # noqa: E501


@pytest.fixture
def mock_audio_interface():
    """Create a mock AudioInterface instance."""
    with patch("src.audioGuestBook.AudioInterface") as mock:
        instance = mock.return_value
        instance.play_audio = MagicMock()
        instance.start_recording = MagicMock()
        instance.stop_recording = MagicMock()
        instance.stop_playback = MagicMock()
        yield instance


@pytest.fixture
def mock_button():
    """Create a mock Button instance."""
    with patch("src.audioGuestBook.Button") as mock:
        instance = mock.return_value
        instance.when_pressed = None
        instance.when_released = None
        yield instance


@pytest.fixture
def guest_book(mock_config, tmp_path):
    """Create an AudioGuestBook instance with test configuration."""
    # Create a temporary config file
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(mock_config, f)

    with (
        patch("src.audioGuestBook.AudioInterface"),
        patch("src.audioGuestBook.Button"),
    ):
        return AudioGuestBook(str(config_path))


def test_init(guest_book, mock_config):
    """Test AudioGuestBook initialization."""
    assert guest_book.config == mock_config
    assert guest_book.current_event == CurrentEvent.NONE
    assert isinstance(guest_book.audio_interface, MagicMock)


def test_load_config_file_not_found(tmp_path):
    """Test loading non-existent configuration file."""
    with pytest.raises(SystemExit):
        AudioGuestBook(str(tmp_path / "nonexistent.yaml"))


def test_setup_hook_nc(guest_book, mock_button):
    """Test hook setup for NC type."""
    guest_book.config["hook_type"] = "NC"
    guest_book.config["invert_hook"] = False

    guest_book.setup_hook()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(17, pull_up=True, bounce_time=0.1)

    # Verify event handlers were set correctly
    assert mock_button.return_value.when_pressed == guest_book.off_hook
    assert mock_button.return_value.when_released == guest_book.on_hook


def test_setup_hook_no(guest_book, mock_button):
    """Test hook setup for NO type."""
    guest_book.config["hook_type"] = "NO"
    guest_book.config["invert_hook"] = False

    guest_book.setup_hook()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(17, pull_up=False, bounce_time=0.1)

    # Verify event handlers were set correctly
    assert mock_button.return_value.when_pressed == guest_book.on_hook
    assert mock_button.return_value.when_released == guest_book.off_hook


def test_off_hook(guest_book, mock_audio_interface):
    """Test off-hook event handling."""
    # Simulate another event in progress
    guest_book.current_event = CurrentEvent.RECORD_GREETING
    guest_book.off_hook()
    mock_audio_interface.play_audio.assert_not_called()

    # Reset state and test normal off-hook
    guest_book.current_event = CurrentEvent.NONE
    guest_book.off_hook()

    # Verify greeting playback was started
    assert guest_book.current_event == CurrentEvent.HOOK
    assert isinstance(guest_book.greeting_thread, threading.Thread)
    assert guest_book.greeting_thread.is_alive()


def test_on_hook(guest_book, mock_audio_interface):
    """Test on-hook event handling."""
    # Set up initial state
    guest_book.current_event = CurrentEvent.HOOK
    guest_book.greeting_thread = threading.Thread(target=lambda: None)
    guest_book.greeting_thread.start()

    guest_book.on_hook()

    # Verify state was reset
    assert guest_book.current_event == CurrentEvent.NONE
    mock_audio_interface.stop_recording.assert_called_once()
    mock_audio_interface.stop_playback.assert_called_once()


def test_play_greeting_and_beep(guest_book, mock_audio_interface, tmp_path):
    """Test greeting and beep playback sequence."""
    # Create temporary audio files
    greeting_file = tmp_path / "greeting.wav"
    beep_file = tmp_path / "beep.wav"
    greeting_file.touch()
    beep_file.touch()

    guest_book.config["greeting"] = str(greeting_file)
    guest_book.config["beep"] = str(beep_file)
    guest_book.config["beep_include_in_message"] = True

    # Set up recording path
    recordings_path = tmp_path / "recordings"
    recordings_path.mkdir()
    guest_book.config["recordings_path"] = str(recordings_path)

    guest_book.play_greeting_and_beep()

    # Verify greeting was played
    mock_audio_interface.play_audio.assert_any_call(str(greeting_file), 0.8, 0)

    # Verify beep was played
    mock_audio_interface.play_audio.assert_any_call(str(beep_file), 0.8, 0)

    # Verify recording was started
    mock_audio_interface.start_recording.assert_called_once()


def test_time_exceeded(guest_book, mock_audio_interface):
    """Test time exceeded event handling."""
    guest_book.time_exceeded()

    # Verify recording was stopped and time exceeded message was played
    mock_audio_interface.stop_recording.assert_called_once()
    mock_audio_interface.play_audio.assert_called_once_with(
        "/path/to/time_exceeded.wav", 0.8, 0
    )


def test_setup_record_greeting(guest_book, mock_button):
    """Test record greeting button setup."""
    guest_book.setup_record_greeting()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(27, pull_up=True, bounce_time=0.1)

    # Verify event handlers were set correctly
    assert mock_button.return_value.when_pressed == guest_book.pressed_record_greeting
    assert mock_button.return_value.when_released == guest_book.released_record_greeting


def test_setup_record_greeting_disabled(guest_book, mock_button):
    """Test record greeting setup when disabled."""
    guest_book.config["record_greeting_gpio"] = 0
    guest_book.setup_record_greeting()
    mock_button.assert_not_called()


def test_stop_recording_and_playback(guest_book, mock_audio_interface):
    """Test stopping recording and playback."""
    # Set up initial state
    guest_book.greeting_thread = threading.Thread(target=lambda: None)
    guest_book.greeting_thread.start()

    guest_book.stop_recording_and_playback()

    # Verify audio processes were stopped
    mock_audio_interface.stop_recording.assert_called_once()
    mock_audio_interface.stop_playback.assert_called_once()

    # Verify timer was cancelled if it existed
    if hasattr(guest_book, "timer"):
        assert not guest_book.timer.is_alive()
