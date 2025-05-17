import threading
from unittest.mock import MagicMock, patch, Mock

import pytest
import yaml
from pathlib import Path

from rotary_guestbook.audioGuestBook import AudioGuestBook, CurrentEvent


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
    # Reverting to simple MagicMock as autospec didn't solve the main issue
    # and complicated test_init.
    with patch("rotary_guestbook.audioGuestBook.AudioInterface") as mock_class:
        yield mock_class.return_value


@pytest.fixture
def mock_button():
    """Create a mock Button CLASS and yield it."""
    with patch("rotary_guestbook.audioGuestBook.Button") as mock_class:
        # The code under test will call mock_class() to get an instance.
        # That instance (mock_class.return_value) will be a MagicMock
        # by default. Attributes like .when_pressed are set by the code
        # on this instance.
        yield mock_class


@pytest.fixture
def guest_book(mock_config, tmp_path, mock_audio_interface, mock_button):
    """Create an AudioGuestBook instance with test configuration."""
    # Create a temporary config file
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(mock_config, f)

    # The AudioGuestBook will pick up the mocks when it tries to import Button
    # and AudioInterface, because the mock_audio_interface and mock_button
    # fixtures have already patched them.
    return AudioGuestBook(str(config_path))


def test_init(guest_book, mock_config):
    """Test AudioGuestBook initialization."""
    assert guest_book.config == mock_config
    assert guest_book.current_event == CurrentEvent.NONE
    # Check if it's an instance of the general Mock class
    assert isinstance(guest_book.audio_interface, Mock)


def test_load_config_file_not_found(tmp_path):
    """Test loading non-existent configuration file."""
    with pytest.raises(SystemExit):
        AudioGuestBook(str(tmp_path / "nonexistent.yaml"))


def test_setup_hook_nc(guest_book, mock_button):
    """Test hook setup for NC type."""
    guest_book.config["hook_type"] = "NC"
    guest_book.config["invert_hook"] = False

    mock_button.reset_mock()  # Reset calls from __init__
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

    mock_button.reset_mock()  # Reset calls from __init__
    guest_book.setup_hook()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(17, pull_up=False, bounce_time=0.1)

    # Verify event handlers were set correctly
    assert mock_button.return_value.when_pressed == guest_book.on_hook
    assert mock_button.return_value.when_released == guest_book.off_hook


def test_setup_hook_nc_inverted(guest_book, mock_button):
    """Test hook setup for NC type with invert_hook=True."""
    guest_book.config["hook_type"] = "NC"
    guest_book.config["invert_hook"] = True

    mock_button.reset_mock()  # Reset calls from __init__
    guest_book.setup_hook()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(17, pull_up=True, bounce_time=0.1)

    # Verify event handlers were set for inverted NC
    assert mock_button.return_value.when_released == guest_book.off_hook
    assert mock_button.return_value.when_pressed == guest_book.on_hook


def test_setup_hook_no_inverted(guest_book, mock_button):
    """Test hook setup for NO type with invert_hook=True."""
    guest_book.config["hook_type"] = "NO"
    guest_book.config["invert_hook"] = True

    mock_button.reset_mock()  # Reset calls from __init__
    guest_book.setup_hook()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(17, pull_up=False, bounce_time=0.1)

    # Verify event handlers were set for inverted NO
    assert mock_button.return_value.when_released == guest_book.on_hook
    assert mock_button.return_value.when_pressed == guest_book.off_hook


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
    assert guest_book.audio_interface is mock_audio_interface

    guest_book.current_event = CurrentEvent.HOOK
    guest_book.greeting_thread = threading.Thread(target=lambda: None)
    guest_book.greeting_thread.start()

    mock_audio_interface.stop_recording.reset_mock()
    mock_audio_interface.stop_playback.reset_mock()

    # Explicitly set up mock attributes that will be checked/used
    mock_audio_interface.recording_process = MagicMock()
    mock_audio_interface.playback_process = MagicMock()
    mock_audio_interface.stop_recording.side_effect = None

    assert guest_book.audio_interface.recording_process  # Verify truthy
    assert guest_book.audio_interface.playback_process  # Verify truthy

    guest_book.on_hook()

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

    # Ensure event is HOOK for beep
    guest_book.current_event = CurrentEvent.HOOK
    guest_book.play_greeting_and_beep()

    # Verify greeting was played
    mock_audio_interface.play_audio.assert_any_call(str(greeting_file), 0.8, 0)

    # Verify beep was played
    mock_audio_interface.play_audio.assert_any_call(str(beep_file), 0.8, 0)

    # Verify recording was started
    mock_audio_interface.start_recording.assert_called_once()


def test_play_greeting_and_beep_record_after_beep(
    guest_book, mock_audio_interface, tmp_path
):
    """Test greeting and beep sequence with recording starting after beep."""
    greeting_file = tmp_path / "greeting.wav"
    beep_file = tmp_path / "beep.wav"
    greeting_file.touch()
    beep_file.touch()

    guest_book.config["greeting"] = str(greeting_file)
    guest_book.config["beep"] = str(beep_file)
    guest_book.config["beep_include_in_message"] = False  # Key change

    recordings_path = tmp_path / "recordings"
    recordings_path.mkdir()
    guest_book.config["recordings_path"] = str(recordings_path)

    guest_book.current_event = CurrentEvent.HOOK

    # Reset mocks to check call order
    mock_audio_interface.reset_mock()

    guest_book.play_greeting_and_beep()

    # Verify greeting and beep were played
    mock_audio_interface.play_audio.assert_any_call(str(greeting_file), 0.8, 0)
    mock_audio_interface.play_audio.assert_any_call(str(beep_file), 0.8, 0)

    # Verify recording was started (we need its args for ordering)
    mock_audio_interface.start_recording.assert_called_once()
    # output_file_name = mock_audio_interface.start_recording.call_args.args[0]

    # Check the order of calls: beep should be played before recording starts
    # Greeting is played even before beep.
    # from unittest.mock import call # Removed unused import

    # Expected sequence of relevant calls:
    # 1. play_audio(greeting_file, ...)
    # 2. play_audio(beep_file, ...)
    # 3. start_recording(...)

    # Find the calls in the mock_calls list
    greeting_call_index = -1
    beep_call_index = -1
    start_recording_call_index = -1

    for idx, c_obj in enumerate(mock_audio_interface.mock_calls):
        method_name = c_obj[0]  # Name of the method as string
        args = c_obj[1]  # Tuple of arguments
        # kwargs = c_obj[2]     # Dictionary of keyword arguments (if any)

        if method_name == "play_audio":
            if args[0] == str(greeting_file):
                greeting_call_index = idx
            elif args[0] == str(beep_file):
                beep_call_index = idx
        elif method_name == "start_recording":
            start_recording_call_index = idx

    assert greeting_call_index != -1, "Greeting play_audio call not found in mock_calls"
    assert beep_call_index != -1, "Beep play_audio call not found in mock_calls"
    assert (
        start_recording_call_index != -1
    ), "start_recording call not found in mock_calls"

    assert greeting_call_index < beep_call_index, "Greeting was not played before beep"
    assert (
        beep_call_index < start_recording_call_index
    ), "start_recording was not called after beep"


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
    mock_button.reset_mock()  # Reset calls from __init__
    guest_book.setup_record_greeting()

    # Verify button was created with correct parameters
    mock_button.assert_called_once_with(27, pull_up=True, bounce_time=0.1)

    # Verify event handlers were set correctly
    assert mock_button.return_value.when_pressed == guest_book.pressed_record_greeting
    assert mock_button.return_value.when_released == guest_book.released_record_greeting


def test_setup_record_greeting_disabled(guest_book, mock_button):
    """Test record greeting setup when disabled."""
    guest_book.config["record_greeting_gpio"] = 0
    mock_button.reset_mock()  # Reset calls from __init__
    guest_book.setup_record_greeting()
    mock_button.assert_not_called()


def test_stop_recording_and_playback(guest_book, mock_audio_interface):
    """Test stopping recording and playback."""
    assert guest_book.audio_interface is mock_audio_interface

    guest_book.greeting_thread = threading.Thread(target=lambda: None)
    guest_book.greeting_thread.start()

    mock_audio_interface.stop_recording.reset_mock()
    mock_audio_interface.stop_playback.reset_mock()

    # Explicitly set up mock attributes that will be checked/used
    mock_audio_interface.recording_process = MagicMock()
    mock_audio_interface.playback_process = MagicMock()
    mock_audio_interface.stop_recording.side_effect = None

    assert guest_book.audio_interface.recording_process  # Verify truthy
    assert guest_book.audio_interface.playback_process  # Verify truthy

    guest_book.stop_recording_and_playback()

    mock_audio_interface.stop_recording.assert_called_once()
    mock_audio_interface.stop_playback.assert_called_once()

    # Verify timer was cancelled if it existed
    if hasattr(guest_book, "timer"):
        assert not guest_book.timer.is_alive()


def test_pressed_record_greeting_when_busy(guest_book, mock_audio_interface):
    """Test pressed_record_greeting is ignored if another event is active."""
    guest_book.current_event = CurrentEvent.HOOK  # Simulate another event
    mock_audio_interface.reset_mock()

    guest_book.pressed_record_greeting()

    mock_audio_interface.play_audio.assert_not_called()
    mock_audio_interface.start_recording.assert_not_called()
    assert guest_book.current_event == CurrentEvent.HOOK
    assert (
        not hasattr(guest_book, "greeting_thread")
        or guest_book.greeting_thread.target != guest_book.beep_and_record_greeting
    )


def test_pressed_record_greeting_starts_sequence(guest_book, mock_audio_interface):
    """Test pressed_record_greeting starts the beep_and_record_greeting sequence."""
    guest_book.current_event = CurrentEvent.NONE

    # Patch the target method of the thread to verify it's called
    with patch.object(guest_book, "beep_and_record_greeting") as mock_beep_and_record:
        guest_book.pressed_record_greeting()

        assert guest_book.current_event == CurrentEvent.RECORD_GREETING
        assert isinstance(guest_book.greeting_thread, threading.Thread)
        # guest_book.greeting_thread.is_alive() is likely False as mock runs fast.
        # The key is that the mock target was called.

        # The mock should be called by the thread. If the thread daemon status matters
        # or if it needs more time, this might need adjustment.
        # For a simple mock call, this should be near-instantaneous.
        mock_beep_and_record.assert_called_once()


def test_released_record_greeting_when_not_recording_greeting(guest_book):
    """Test released_record_greeting does nothing if not in RECORD_GREETING state."""
    guest_book.current_event = CurrentEvent.NONE
    with patch.object(guest_book, "stop_recording_and_playback") as mock_stop_all:
        guest_book.released_record_greeting()
        mock_stop_all.assert_not_called()
        assert guest_book.current_event == CurrentEvent.NONE

    # Also test with HOOK event, for example
    guest_book.current_event = CurrentEvent.HOOK
    with patch.object(guest_book, "stop_recording_and_playback") as mock_stop_all:
        guest_book.released_record_greeting()
        mock_stop_all.assert_not_called()
        assert guest_book.current_event == CurrentEvent.HOOK


def test_released_record_greeting_stops_sequence(guest_book):
    """Test released_record_greeting stops the sequence and resets state."""
    guest_book.current_event = CurrentEvent.RECORD_GREETING
    with patch.object(guest_book, "stop_recording_and_playback") as mock_stop_all:
        guest_book.released_record_greeting()
        assert guest_book.current_event == CurrentEvent.NONE
        mock_stop_all.assert_called_once()


def test_beep_and_record_greeting(guest_book, mock_audio_interface, tmp_path):
    """Test beep_and_record_greeting plays beep and starts recording greeting."""
    guest_book.current_event = CurrentEvent.RECORD_GREETING

    beep_file = guest_book.config["beep"]  # This can stay as is from mock_config

    # Create a temporary path for the greeting file for this test
    temp_greeting_dir = tmp_path / "greetings"
    # No need to mkdir for temp_greeting_dir, Path.parent.mkdir will handle it.
    greeting_file_path_obj = temp_greeting_dir / "new_greeting.wav"
    guest_book.config["greeting"] = str(greeting_file_path_obj)
    # The actual greeting_file_path to be used by the method under test
    greeting_file_path_for_method = str(greeting_file_path_obj)

    # Ensure the greeting file path directory exists.
    # This will now operate within the tmp_path sandbox.
    Path(greeting_file_path_for_method).parent.mkdir(parents=True, exist_ok=True)

    mock_audio_interface.reset_mock()
    guest_book.beep_and_record_greeting()

    # Assert beep was played and recording was started for the greeting file
    mock_audio_interface.play_audio.assert_any_call(
        beep_file,
        guest_book.config["beep_volume"],
        guest_book.config["beep_start_delay"],
    )
    mock_audio_interface.start_recording.assert_called_once_with(
        greeting_file_path_for_method
    )

    # Check call order: beep before recording
    beep_call_index = -1
    start_recording_call_index = -1

    for idx, c_obj in enumerate(mock_audio_interface.mock_calls):
        method_name = c_obj[0]
        args = c_obj[1]
        if method_name == "play_audio" and args[0] == beep_file:
            beep_call_index = idx
        elif (
            method_name == "start_recording"
            and args[0] == greeting_file_path_for_method
        ):
            start_recording_call_index = idx

    assert beep_call_index != -1, "Beep play_audio call not found"
    assert start_recording_call_index != -1, "Greeting start_recording call not found"
    assert (
        beep_call_index < start_recording_call_index
    ), "Beep was not played before recording greeting"


def test_setup_shutdown_button(guest_book, mock_button):
    """Test shutdown button setup."""
    # Ensure config has default values for shutdown button
    guest_book.config["shutdown_gpio"] = 22  # As per default mock_config
    guest_book.config["shutdown_button_hold_time"] = 2  # As per default mock_config

    mock_button.reset_mock()
    guest_book.setup_shutdown_button()

    expected_hold_time = guest_book.config["shutdown_button_hold_time"]
    mock_button.assert_called_once_with(
        guest_book.config["shutdown_gpio"], pull_up=True, hold_time=expected_hold_time
    )
    assert mock_button.return_value.when_held == guest_book.shutdown


def test_setup_shutdown_button_disabled(guest_book, mock_button):
    """Test shutdown button setup when GPIO is 0 (disabled)."""
    guest_book.config["shutdown_gpio"] = 0
    mock_button.reset_mock()

    guest_book.setup_shutdown_button()

    mock_button.assert_not_called()


# End of tests
