"""Unit tests for the audio module.

These tests cover AudioManager and PyAudioBackend, mocking external dependencies.
"""

import logging
import sys
from typing import Any, Generator
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError, CouldntEncodeError

from rotary_guestbook.audio import AbstractAudioBackend, AudioManager, PyAudioBackend
from rotary_guestbook.config import (
    AudioSettings,
    ConfigManager,
    ConversionSettings,
    RecordingSettings,
)
from rotary_guestbook.errors import AudioError, ConfigError

# Disable verbose logging from dependencies during tests
logging.getLogger("pydub").setLevel(logging.WARNING)


@pytest.fixture
def mock_audio_backend() -> MagicMock:
    """Fixture for a MagicMock of AbstractAudioBackend."""
    return MagicMock(spec=AbstractAudioBackend)


@pytest.fixture
def mock_config_manager() -> MagicMock:
    """Fixture for a MagicMock of ConfigManager."""
    mock = MagicMock(spec=ConfigManager)

    # Mock the nested structure
    mock_conversion_settings = MagicMock(spec=ConversionSettings)
    mock_conversion_settings.mp3_bitrate = "192k"
    mock_conversion_settings.ffmpeg_parameters = ["-v", "quiet"]

    mock_recording_settings = MagicMock(spec=RecordingSettings)
    mock_recording_settings.input_device_index = None
    mock_recording_settings.channels = 1
    mock_recording_settings.rate = 44100
    mock_recording_settings.sample_width = 2
    mock_recording_settings.chunk_size = 1024
    mock_recording_settings.max_duration_seconds = 180

    mock_audio_settings = MagicMock(spec=AudioSettings)
    mock_audio_settings.greeting_message_path = "path/to/greeting.wav"
    mock_audio_settings.output_device_index = None
    mock_audio_settings.min_recording_time = 3
    mock_audio_settings.silence_threshold = 0.01
    mock_audio_settings.silence_duration = 2
    mock_audio_settings.output_directory = "recordings"
    mock_audio_settings.recording = mock_recording_settings
    mock_audio_settings.conversion = mock_conversion_settings

    # ConfigManager.audio property returns the mocked AudioSettings
    type(mock).audio = PropertyMock(return_value=mock_audio_settings)
    # Keep get_audio_config for now if AudioManager still uses it, but align its return
    mock.get_audio_config.return_value = mock_audio_settings
    return mock


class DummyAudioBackend(AbstractAudioBackend):
    """Implement a dummy AbstractAudioBackend for testing coverage."""

    def play_greeting(self) -> None:
        """Simulate playing a greeting."""
        super().play_greeting()

    def start_recording(self, filename: str) -> None:
        """Simulate starting a recording."""
        super().start_recording(filename)

    def stop_recording(self) -> None:
        """Simulate stopping a recording."""
        super().stop_recording()

    def convert_to_mp3(self, input_wav: str, output_mp3: str) -> None:
        """Simulate converting WAV to MP3."""
        super().convert_to_mp3(input_wav, output_mp3)


class TestAbstractAudioBackend:
    """Tests for the AbstractAudioBackend to cover abstract methods."""

    def test_abstract_methods_callable_for_coverage(self) -> None:
        """Call abstract methods on a dummy subclass to cover `pass` statements."""
        backend = DummyAudioBackend()
        # These calls cover the `pass` statements in the abstract methods.
        # No exception is expected here because the methods are defined with `pass`.
        backend.play_greeting()
        backend.start_recording("test.wav")
        backend.stop_recording()
        backend.convert_to_mp3("in.wav", "out.mp3")


class TestAudioManager:
    """Tests for the AudioManager class."""

    def test_initialization(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test AudioManager initializes correctly."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        assert am._audio_backend is mock_audio_backend
        assert am._audio_settings is mock_config_manager.audio
        assert not am.is_recording

    def test_play_greeting_success(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting calls backend and handles success."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.play_greeting()
        mock_audio_backend.play_greeting.assert_called_once()

    def test_play_greeting_no_path(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting skips if no greeting path is configured."""
        mock_config_manager.audio.greeting_message_path = None
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.play_greeting()
        mock_audio_backend.play_greeting.assert_not_called()

    def test_play_greeting_backend_audio_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting raises AudioError if backend raises AudioError."""
        mock_audio_backend.play_greeting.side_effect = AudioError("Backend failed")
        am = AudioManager(mock_audio_backend, mock_config_manager)
        with pytest.raises(AudioError, match="Backend failed"):
            am.play_greeting()

    def test_play_greeting_backend_unexpected_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting raises AudioError for unexpected backend errors."""
        exc = Exception("Unexpected backend fail")
        mock_audio_backend.play_greeting.side_effect = exc
        am = AudioManager(mock_audio_backend, mock_config_manager)
        with pytest.raises(AudioError, match="Failed to play greeting"):
            am.play_greeting()

    def test_start_recording_success(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test start_recording calls backend and sets recording state."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.start_recording("test_message")
        mock_audio_backend.start_recording.assert_called_once_with("test_message.wav")
        assert am.is_recording

    def test_start_recording_already_recording(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test start_recording raises AudioError if already recording."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.start_recording("test_message1")
        assert am.is_recording
        with pytest.raises(AudioError, match="Recording is already in progress"):
            am.start_recording("test_message2")
        # Ensure backend was only called once
        mock_audio_backend.start_recording.assert_called_once_with("test_message1.wav")

    def test_start_recording_backend_audio_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test start_recording raises AudioError if backend fails."""
        mock_audio_backend.start_recording.side_effect = AudioError(
            "Backend start failed"
        )
        am = AudioManager(mock_audio_backend, mock_config_manager)
        with pytest.raises(AudioError, match="Backend start failed"):
            am.start_recording("test_message")
        assert not am.is_recording

    def test_stop_recording_success(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording calls backend and resets recording state."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.start_recording("test_message")  # Start first
        assert am.is_recording
        am.stop_recording()
        mock_audio_backend.stop_recording.assert_called_once()
        assert not am.is_recording

    def test_stop_recording_not_recording(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording raises AudioError if not recording."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        assert not am.is_recording
        with pytest.raises(AudioError, match="Recording is not in progress"):
            am.stop_recording()
        mock_audio_backend.stop_recording.assert_not_called()

    def test_stop_recording_backend_audio_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording raises AudioError if backend fails."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.start_recording("test_message")
        mock_audio_backend.stop_recording.side_effect = AudioError(
            "Backend stop failed"
        )
        with pytest.raises(AudioError, match="Backend stop failed"):
            am.stop_recording()
        # is_recording should still be False as AudioManager attempts to set it
        # before re-raising the error from backend, or after a successful call.
        assert not am.is_recording

    def test_stop_recording_backend_unexpected_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording raises AudioError for unexpected backend errors."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.start_recording("test_message")  # Start recording first
        assert am.is_recording

        exc = Exception("Unexpected backend stop fail")
        mock_audio_backend.stop_recording.side_effect = exc

        with pytest.raises(AudioError, match="Failed to stop recording") as exc_info:
            am.stop_recording()
        assert exc_info.value.details == str(exc)
        assert not am.is_recording

    def test_convert_to_mp3_success(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test convert_to_mp3 calls backend successfully."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        am.convert_to_mp3("input.wav", "output.mp3")
        mock_audio_backend.convert_to_mp3.assert_called_once_with(
            "input.wav", "output.mp3"
        )

    def test_convert_to_mp3_backend_file_not_found(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test convert_to_mp3 propagates FileNotFoundError from backend."""
        mock_audio_backend.convert_to_mp3.side_effect = FileNotFoundError(
            "input.wav not found"
        )
        am = AudioManager(mock_audio_backend, mock_config_manager)
        with pytest.raises(FileNotFoundError):
            am.convert_to_mp3("input.wav", "output.mp3")

    def test_convert_to_mp3_backend_audio_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test convert_to_mp3 propagates AudioError from backend."""
        mock_audio_backend.convert_to_mp3.side_effect = AudioError("Conversion failed")
        am = AudioManager(mock_audio_backend, mock_config_manager)
        with pytest.raises(AudioError, match="Conversion failed"):
            am.convert_to_mp3("input.wav", "output.mp3")

    def test_convert_to_mp3_backend_unexpected_error(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test convert_to_mp3 raises AudioError for unexpected backend errors."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        exc = Exception("Unexpected backend conversion fail")
        mock_audio_backend.convert_to_mp3.side_effect = exc

        with pytest.raises(
            AudioError, match="Failed to convert input.wav to MP3"
        ) as exc_info:
            am.convert_to_mp3("input.wav", "output.mp3")
        assert exc_info.value.details == str(exc)

    def test_is_recording_property(
        self, mock_audio_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test the is_recording property."""
        am = AudioManager(mock_audio_backend, mock_config_manager)
        assert not am.is_recording
        am.start_recording("test")
        assert am.is_recording
        am.stop_recording()  # type: ignore
        assert not am.is_recording


# --- PyAudioBackend Tests ---


@pytest.fixture
def mock_pyaudio_core_module() -> Generator[MagicMock, None, None]:
    """Mock the 'pyaudio' module using sys.modules."""
    mock_module = MagicMock(name="mock_pyaudio_module")
    mock_module.paContinue = 0

    # Try to import real pyaudio for speccing, fallback to MagicMock class
    try:
        import pyaudio as real_pyaudio

        PyAudio_spec_class = real_pyaudio.PyAudio
        Stream_spec_class = real_pyaudio.Stream
    except ImportError:
        PyAudio_spec_class = MagicMock  # Fallback to MagicMock class for speccing
        Stream_spec_class = MagicMock  # Fallback to MagicMock class for speccing

    # mock_module.PyAudio is a mock OF the PyAudio CLASS
    mock_module.PyAudio = MagicMock(spec=PyAudio_spec_class, name="MockPyAudioClass")
    # mock_module.Stream is a mock OF the Stream CLASS
    mock_module.Stream = MagicMock(spec=Stream_spec_class, name="MockStreamClass")

    mock_module.get_format_from_width = MagicMock(side_effect=lambda width: width)

    # Store the spec classes on the mock_module for downstream fixtures
    mock_module._PyAudio_spec_class = PyAudio_spec_class
    mock_module._Stream_spec_class = Stream_spec_class

    orig_pyaudio = sys.modules.get("pyaudio")
    sys.modules["pyaudio"] = mock_module

    yield mock_module

    # Cleanup: Restore original pyaudio in sys.modules if it existed, else remove ours.
    if orig_pyaudio:
        sys.modules["pyaudio"] = orig_pyaudio
    elif "pyaudio" in sys.modules and sys.modules["pyaudio"] is mock_module:
        del sys.modules["pyaudio"]


@pytest.fixture
def configured_mock_pyaudio_instance(
    mock_pyaudio_core_module: MagicMock,
) -> MagicMock:
    """Create a mock PyAudio() instance with specced internal stream mocks.

    This uses spec classes from the mock_pyaudio_core_module.
    """
    # Use the stored spec *class* for speccing new MagicMock instances
    mock_stream = MagicMock(spec=mock_pyaudio_core_module._Stream_spec_class)
    mock_stream.is_active.return_value = False
    mock_stream.write = MagicMock()
    mock_stream.stop_stream = MagicMock()
    mock_stream.close = MagicMock()
    mock_stream.start_stream = MagicMock()

    # This mock_instance simulates an *instance* of PyAudio
    mock_instance = MagicMock(spec=mock_pyaudio_core_module._PyAudio_spec_class)
    mock_instance.open.return_value = mock_stream
    # get_format_from_width is a module-level function in pyaudio, proxied here
    mock_instance.get_format_from_width = mock_pyaudio_core_module.get_format_from_width
    mock_instance.terminate = MagicMock()
    return mock_instance


@pytest.fixture
def mock_pyaudio_fully_specced(
    mock_pyaudio_core_module: MagicMock, configured_mock_pyaudio_instance: MagicMock
) -> MagicMock:
    """Ensure 'rotary_guestbook.audio.pyaudio' is patched.

    Ensures PyAudio() returns a fully specced mock instance.
    Returns the patched module mock.
    """
    mock_pyaudio_core_module.PyAudio.return_value = configured_mock_pyaudio_instance
    return mock_pyaudio_core_module


@pytest.fixture
def mock_audio_segment_class_object() -> MagicMock:
    """Return a MagicMock that simulates AudioSegment class structure via autospec."""
    # Use autospec=True based on the imported pydub.AudioSegment
    mock_class = MagicMock(name="MockAudioSegmentClass_Autospec", autospec=AudioSegment)

    # Autospec means mock_class() returns an instance mock (also autospecced).
    # Let's call this instance_mock. We need to ensure its .export is a MagicMock.
    instance_mock = mock_class.return_value
    instance_mock.export = MagicMock(name="MockAudioSegmentInstance.export")

    # For methods like from_file and from_wav, which are class methods that return
    # an AudioSegment instance, their mocks (created by autospec on mock_class)
    # should also return our configured instance_mock.
    # mock_class.from_file is already a MagicMock due to autospec.
    # mock_class.from_wav is already a MagicMock due to autospec.
    mock_class.from_file.return_value = instance_mock
    mock_class.from_wav.return_value = instance_mock

    # If AudioSegment has other static/class methods that return instances,
    # they would need similar treatment if used by the code under test.

    return mock_class


class TestPyAudioBackend:
    """Tests for the PyAudioBackend class."""

    DUMMY_WAV = "dummy.wav"
    DUMMY_MP3 = "dummy.mp3"

    @pytest.fixture(autouse=True)
    def setup_mocks(
        self,
        mock_pyaudio_fully_specced: MagicMock,
        mock_audio_segment_class_object: MagicMock,
        request: Any,
    ) -> None:
        """Ensure PyAudio and AudioSegment are mocked for all tests in this class."""
        self.mock_pyaudio_module = mock_pyaudio_fully_specced
        self.mock_pyaudio_instance = self.mock_pyaudio_module.PyAudio.return_value
        self.mock_pyaudio_module.PyAudio.reset_mock()

        patcher = patch(
            "rotary_guestbook.audio.AudioSegment", new=mock_audio_segment_class_object
        )
        self.mock_audio_segment_class = patcher.start()
        request.addfinalizer(patcher.stop)

    @pytest.fixture
    def backend(self, mock_config_manager: MagicMock) -> PyAudioBackend:
        """Fixture to get a PyAudioBackend instance with a mocked config."""
        return PyAudioBackend(mock_config_manager)

    def test_initialize_pyaudio_success(self, backend: PyAudioBackend) -> None:
        """Test that _initialize_pyaudio loads PyAudio correctly."""
        backend._initialize_pyaudio()
        self.mock_pyaudio_module.PyAudio.assert_called_once()
        assert backend._pyaudio_instance is self.mock_pyaudio_instance

        backend._initialize_pyaudio()
        self.mock_pyaudio_module.PyAudio.assert_called_once()

    @patch.dict(sys.modules, {"pyaudio": None})
    def test_initialize_pyaudio_import_error(self, backend: PyAudioBackend) -> None:
        """Test _initialize_pyaudio raises AudioError if PyAudio is not found."""
        backend._pyaudio_instance = None
        with pytest.raises(AudioError, match="PyAudio library not found"):
            backend._initialize_pyaudio()

    def test_initialize_pyaudio_instantiation_fails(
        self, backend: PyAudioBackend
    ) -> None:
        """Test _initialize_pyaudio raises AudioError if PyAudio() fails."""
        self.mock_pyaudio_module.PyAudio.side_effect = RuntimeError(
            "PyAudio init failed"
        )
        backend._pyaudio_instance = None  # Ensure it tries to initialize
        with pytest.raises(
            AudioError, match="Failed to initialize PyAudio"
        ) as exc_info:
            backend._initialize_pyaudio()
        assert exc_info.value.details == "PyAudio init failed"

    def test_play_greeting_success(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test playing a greeting successfully."""
        greeting_path = "sounds/greeting.wav"
        mock_config_manager.audio.greeting_message_path = greeting_path

        # Configure the attributes of the instance_mock that from_file will return
        # self.mock_audio_segment_class is the autospecced mock_class
        # self.mock_audio_segment_class.from_file.return_value is instance_mock
        returned_segment_mock = self.mock_audio_segment_class.from_file.return_value
        returned_segment_mock.sample_width = 2
        returned_segment_mock.channels = 1
        returned_segment_mock.frame_rate = 44100
        returned_segment_mock.raw_data = b"d_chunk" * 20

        # The mock stream is returned by self.mock_pyaudio_instance.open()
        mock_stream = self.mock_pyaudio_instance.open.return_value
        if not isinstance(mock_stream.write, MagicMock):
            mock_stream.write = MagicMock(name="MockStream.write")

        backend.play_greeting()

        self.mock_audio_segment_class.from_file.assert_called_once_with(greeting_path)
        self.mock_pyaudio_instance.open.assert_called_once_with(
            format=self.mock_pyaudio_instance.get_format_from_width(
                returned_segment_mock.sample_width
            ),
            channels=returned_segment_mock.channels,  # Use from returned_segment_mock
            rate=returned_segment_mock.frame_rate,  # Use from returned_segment_mock
            output=True,
            output_device_index=mock_config_manager.audio.output_device_index,
        )

        opened_stream = self.mock_pyaudio_instance.open.return_value
        opened_stream.write.assert_called()
        opened_stream.stop_stream.assert_called_once()
        opened_stream.close.assert_called_once()

    def test_play_greeting_no_path_configured(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting raises ConfigError if path is not set."""
        mock_config_manager.audio.greeting_message_path = None
        with pytest.raises(
            ConfigError, match="Greeting message path is not configured"
        ):
            backend.play_greeting()

    def test_play_greeting_file_not_found(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting raises AudioError if greeting file not found by pydub."""
        greeting_path = "nonexistent.wav"
        mock_config_manager.audio.greeting_message_path = greeting_path
        self.mock_audio_segment_class.from_file.side_effect = FileNotFoundError(
            "Not found"
        )
        with pytest.raises(
            AudioError, match=f"Greeting file not found: {greeting_path}"
        ):
            backend.play_greeting()

    def test_play_greeting_pydub_decode_error(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting handles pydub decoding errors."""
        greeting_path = "corrupt.wav"
        mock_config_manager.audio.greeting_message_path = greeting_path
        self.mock_audio_segment_class.from_file.side_effect = CouldntDecodeError(
            "Decode failed"
        )
        with pytest.raises(
            AudioError, match=f"Could not load greeting file: {greeting_path}"
        ):
            backend.play_greeting()

    def test_play_greeting_pyaudio_open_fails(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting handles PyAudio stream opening failures."""
        dummy_segment = MagicMock()
        self.mock_audio_segment_class.from_file.return_value = dummy_segment

        self.mock_pyaudio_instance.open.side_effect = Exception("Failed to open stream")
        with pytest.raises(AudioError, match="Error playing greeting via PyAudio"):
            backend.play_greeting()

    def test_play_greeting_stream_close_exception_in_finally(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting handles exceptions during stream close in finally."""
        greeting_path = "sounds/greeting.wav"
        mock_config_manager.audio.greeting_message_path = greeting_path

        returned_segment_mock = self.mock_audio_segment_class.from_file.return_value
        returned_segment_mock.sample_width = 2
        returned_segment_mock.channels = 1
        returned_segment_mock.frame_rate = 44100
        returned_segment_mock.raw_data = b"d_chunk" * 20

        mock_stream = self.mock_pyaudio_instance.open.return_value
        mock_stream.stop_stream.side_effect = Exception(
            "Failed to stop stream in finally"
        )

        # We don't expect an error to be raised from play_greeting itself,
        # as the exception happens in finally. The error should be logged.
        # We can check if stop_stream was called.
        backend.play_greeting()
        mock_stream.stop_stream.assert_called_once()
        # Not testing logger output here, focusing on graceful handling.

    def test_play_greeting_stream_becomes_none_mid_playback(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test play_greeting handles stream becoming None during playback loop."""
        greeting_path = "sounds/greeting.wav"
        mock_config_manager.audio.greeting_message_path = greeting_path

        returned_segment_mock = self.mock_audio_segment_class.from_file.return_value
        returned_segment_mock.sample_width = 2
        returned_segment_mock.channels = 1
        returned_segment_mock.frame_rate = 44100
        # Make raw_data long enough to enter the loop more than once if chunked
        returned_segment_mock.raw_data = b"d_chunk" * 20

        mock_stream = self.mock_pyaudio_instance.open.return_value

        # Create a new mock to be the actual target of write operations
        # within the side_effect, to avoid recursion.
        actual_write_target_mock = MagicMock()

        # Simulate stream becoming None after the first write
        # The original mock_stream.write will call our side_effect.
        # Our side_effect will then call actual_write_target_mock.
        def write_side_effect_and_clear_stream(*args: Any, **kwargs: Any) -> None:
            actual_write_target_mock(*args, **kwargs)  # Call the separate mock
            backend._stream = None  # Simulate stream disappearing after one write

        mock_stream.write.side_effect = write_side_effect_and_clear_stream

        backend.play_greeting()

        # Check that our actual_write_target_mock was called at least once
        actual_write_target_mock.assert_called()
        # The loop should break. stop_stream/close on a None stream (no error)
        # is implicitly tested by no error being raised from play_greeting.

    def test_start_recording_success(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test starting a recording successfully."""
        record_settings = mock_config_manager.audio.recording

        backend.start_recording(self.DUMMY_WAV)

        self.mock_pyaudio_instance.open.assert_called_once_with(
            format=record_settings.sample_width,
            channels=record_settings.channels,
            rate=record_settings.rate,
            input=True,
            frames_per_buffer=record_settings.chunk_size,
            input_device_index=record_settings.input_device_index,
            stream_callback=backend._recording_callback,
        )
        opened_stream = self.mock_pyaudio_instance.open()
        opened_stream.start_stream.assert_called_once()
        assert backend._current_recording_filename == self.DUMMY_WAV

    def test_start_recording_stream_already_active(
        self, backend: PyAudioBackend
    ) -> None:
        """Test start_recording raises error if stream is already active.

        Note: PyAudioBackend itself doesn't check this; relies on AudioManager
        or underlying PyAudio errors if open() is called on a busy device.
        This test simulates a direct internal state manipulation.
        """
        backend._stream = MagicMock(spec=self.mock_pyaudio_module._Stream_spec_class)
        assert backend._stream is not None
        backend._stream.is_active.return_value = True
        with pytest.raises(
            AudioError, match="Recording or playback is already in progress"
        ):
            backend.start_recording(self.DUMMY_WAV)

    def test_start_recording_no_config(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test start_recording raises ConfigError if recording config is missing."""
        mock_config_manager.audio.recording = None
        with pytest.raises(
            ConfigError, match="Recording configuration section missing"
        ):
            backend.start_recording(self.DUMMY_WAV)

    def test_start_recording_pyaudio_open_fails(self, backend: PyAudioBackend) -> None:
        """Test start_recording handles PyAudio stream opening failures."""
        self.mock_pyaudio_instance.open.side_effect = Exception(
            "Failed to open input stream"
        )
        with pytest.raises(AudioError, match="Error starting recording via PyAudio"):
            backend.start_recording(self.DUMMY_WAV)
        assert backend._stream is None

    def test_start_recording_pyaudio_open_fails_then_close_fails(
        self, backend: PyAudioBackend
    ) -> None:
        """Test start_recording handles PyAudio open & subsequent close failure."""
        # To hit audio.py lines 383-384 (close fails in handler).
        mocked_stream_for_failed_close = MagicMock(
            spec=self.mock_pyaudio_module._Stream_spec_class
        )
        mocked_stream_for_failed_close.is_active.return_value = (
            False  # stop_stream skipped
        )
        mocked_stream_for_failed_close.close.side_effect = Exception(
            "Close fail in except"
        )

        def open_assigns_then_primary_fail(*args: Any, **kwargs: Any) -> Any:
            backend._stream = mocked_stream_for_failed_close
            raise Exception("Primary open failure")

        self.mock_pyaudio_instance.open.side_effect = open_assigns_then_primary_fail

        with pytest.raises(AudioError, match="Error starting recording via PyAudio"):
            backend.start_recording(self.DUMMY_WAV)

        mocked_stream_for_failed_close.close.assert_called_once()
        assert backend._stream is None

    def test_start_recording_pyaudio_open_fails_stream_active_close_succeeds(
        self, backend: PyAudioBackend
    ) -> None:
        """Test start_recording: open fails, assigned stream is active & closes fine."""
        # To hit audio.py lines 380 & 382 (stop and close succeed in handler).
        mock_problem_stream = MagicMock(
            spec=self.mock_pyaudio_module._Stream_spec_class
        )
        mock_problem_stream.is_active.return_value = True
        mock_problem_stream.stop_stream.return_value = None
        mock_problem_stream.close.return_value = None

        def open_assigns_then_primary_fail_active(*args: Any, **kwargs: Any) -> Any:
            backend._stream = mock_problem_stream
            raise Exception("Primary open failure from mock")

        self.mock_pyaudio_instance.open.side_effect = (
            open_assigns_then_primary_fail_active
        )

        with pytest.raises(AudioError, match="Error starting recording via PyAudio"):
            backend.start_recording(self.DUMMY_WAV)

        mock_problem_stream.is_active.assert_called_once()
        mock_problem_stream.stop_stream.assert_called_once()
        mock_problem_stream.close.assert_called_once()
        assert backend._stream is None

    def test_recording_callback(self, backend: PyAudioBackend) -> None:
        """Test the _recording_callback appends data to frames."""
        dummy_data = b"\x01\x02\x03"
        backend._frames = []

        result_data, result_flag = backend._recording_callback(dummy_data, 100, {}, 0)

        assert backend._frames == [dummy_data]
        assert result_data is None
        assert result_flag == self.mock_pyaudio_module.paContinue

    def test_stop_recording_success_saves_wav(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test stopping a recording successfully saves a WAV file via pydub."""
        mock_active_stream = self.mock_pyaudio_instance.open()
        backend._stream = mock_active_stream
        assert backend._stream is not None
        backend._stream.is_active.return_value = True
        backend._frames = [b"some", b"data"]
        backend._current_recording_filename = self.DUMMY_WAV

        record_settings = mock_config_manager.audio.recording

        backend.stop_recording()

        mock_active_stream.stop_stream.assert_called_once()
        mock_active_stream.close.assert_called_once()
        assert backend._stream is None

        self.mock_audio_segment_class.assert_called_once_with(
            data=b"somedata",
            sample_width=record_settings.sample_width,
            frame_rate=record_settings.rate,
            channels=record_settings.channels,
        )
        mock_segment_instance = self.mock_audio_segment_class()
        mock_segment_instance.export.assert_called_once_with(
            self.DUMMY_WAV, format="wav"
        )
        assert not backend._frames
        assert backend._current_recording_filename is None

    def test_stop_recording_no_active_stream_no_frames(
        self, backend: PyAudioBackend
    ) -> None:
        """Test stop_recording does nothing if no stream and no frames."""
        backend._stream = None
        backend._frames = []
        backend.stop_recording()
        self.mock_audio_segment_class.assert_not_called()
        self.mock_pyaudio_instance.open().stop_stream.assert_not_called()

    def test_stop_recording_inactive_stream_no_frames_closes_stream(
        self, backend: PyAudioBackend
    ) -> None:
        """Test stop_recording closes an inactive stream if no frames exist."""
        mock_inactive_stream = MagicMock()
        mock_inactive_stream.is_active.return_value = False
        backend._stream = mock_inactive_stream
        backend._frames = []

        backend.stop_recording()

        mock_inactive_stream.close.assert_called_once()
        assert backend._stream is None
        self.mock_audio_segment_class.assert_not_called()  # type: ignore

    def test_stop_recording_no_frames_recorded(self, backend: PyAudioBackend) -> None:
        """Test stop_recording does not save WAV if no frames were recorded."""
        backend._stream = self.mock_pyaudio_instance.open()
        backend._stream.is_active.return_value = True
        backend._frames = []
        backend._current_recording_filename = self.DUMMY_WAV

        backend.stop_recording()

        self.mock_audio_segment_class.assert_not_called()
        assert backend._current_recording_filename is None

    def test_stop_recording_no_stream_but_frames_exist_saves_wav(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording saves WAV if _stream is None but _frames exist."""
        backend._stream = None  # Explicitly no stream
        backend._frames = [b"some", b"data"]
        backend._current_recording_filename = self.DUMMY_WAV

        record_settings = mock_config_manager.audio.recording

        backend.stop_recording()

        # Stream related mocks should not be called as stream is None
        self.mock_pyaudio_instance.open().stop_stream.assert_not_called()
        self.mock_pyaudio_instance.open().close.assert_not_called()

        self.mock_audio_segment_class.assert_called_once_with(
            data=b"somedata",
            sample_width=record_settings.sample_width,
            frame_rate=record_settings.rate,
            channels=record_settings.channels,
        )
        mock_segment_instance = self.mock_audio_segment_class()
        mock_segment_instance.export.assert_called_once_with(
            self.DUMMY_WAV, format="wav"
        )
        assert not backend._frames
        assert backend._current_recording_filename is None

    def test_stop_recording_pydub_export_fails(self, backend: PyAudioBackend) -> None:
        """Test stop_recording handles pydub export errors."""
        backend._stream = self.mock_pyaudio_instance.open()
        backend._frames = [b"data"]
        backend._current_recording_filename = self.DUMMY_WAV

        mock_segment_instance = self.mock_audio_segment_class()
        original_error_message = "Export failed due to pydub"
        mock_segment_instance.export.side_effect = CouldntEncodeError(
            original_error_message
        )

        expected_match = f"Unexpected error saving WAV file: {self.DUMMY_WAV}"
        with pytest.raises(AudioError, match=expected_match) as exc_info:
            backend.stop_recording()

        assert exc_info.value.details == original_error_message
        assert not backend._frames
        assert backend._current_recording_filename is None

    def test_stop_recording_pydub_export_ioerror(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording handles IOError during pydub WAV export."""
        backend._stream = self.mock_pyaudio_instance.open()  # Mock stream presence
        backend._stream.is_active.return_value = (
            False  # Assume stopped or was never active
        )
        backend._frames = [b"data"]
        backend._current_recording_filename = self.DUMMY_WAV

        mock_segment_instance = self.mock_audio_segment_class()
        original_error_message = "Export failed due to IOError"
        mock_segment_instance.export.side_effect = IOError(original_error_message)

        expected_match = f"Could not save WAV file: {self.DUMMY_WAV}"
        with pytest.raises(AudioError, match=expected_match) as exc_info:
            backend.stop_recording()

        assert exc_info.value.details == original_error_message
        assert not backend._frames  # Frames should be cleared
        assert backend._current_recording_filename is None  # Filename cleared

    def test_stop_recording_pydub_export_generic_exception(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording handles generic Exception during pydub WAV export."""
        backend._stream = self.mock_pyaudio_instance.open()
        backend._stream.is_active.return_value = False
        backend._frames = [b"data"]
        backend._current_recording_filename = self.DUMMY_WAV

        mock_segment_instance = self.mock_audio_segment_class()
        original_error_message = "Export failed due to generic Exception"
        mock_segment_instance.export.side_effect = Exception(original_error_message)

        # Match the more generic part of the message from audio.py
        expected_match = f"Unexpected error saving WAV file: {self.DUMMY_WAV}"
        with pytest.raises(AudioError, match=expected_match) as exc_info:
            backend.stop_recording()

        assert exc_info.value.details == original_error_message
        assert not backend._frames
        assert backend._current_recording_filename is None

    def test_stop_recording_output_filename_not_set(
        self, backend: PyAudioBackend
    ) -> None:
        """Test stop_recording AudioError if output filename not set."""
        backend._stream = self.mock_pyaudio_instance.open()
        backend._frames = [b"data"]
        backend._current_recording_filename = None

        with pytest.raises(
            AudioError, match="Internal error: output filename for recording not set"
        ):
            backend.stop_recording()

    def test_convert_to_mp3_success(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test converting WAV to MP3 successfully, including with ID3 tags."""
        conversion_settings = mock_config_manager.audio.conversion
        # Add dummy ID3 tags to config for this test path
        conversion_settings.id3_tags = {"artist": "Test Artist", "title": "Test Title"}

        # Ensure from_file mock is properly set up by the fixture
        # self.mock_audio_segment_class.from_file will return an instance_mock
        # whose .export is already a MagicMock.

        backend.convert_to_mp3(self.DUMMY_WAV, self.DUMMY_MP3)

        self.mock_audio_segment_class.from_file.assert_called_once_with(self.DUMMY_WAV)

        returned_segment_mock = self.mock_audio_segment_class.from_file.return_value
        returned_segment_mock.export.assert_called_once_with(
            self.DUMMY_MP3,
            format="mp3",
            bitrate=conversion_settings.mp3_bitrate,
            parameters=conversion_settings.ffmpeg_parameters,
            tags=conversion_settings.id3_tags,  # Verify tags are passed
        )
        # Reset id3_tags if it could affect other tests;
        # fixtures usually isolate this.
        # conversion_settings.id3_tags = None # Reset if needed

    def test_convert_to_mp3_file_not_found(self, backend: PyAudioBackend) -> None:
        """Test convert_to_mp3 raises FileNotFoundError if input WAV is not found."""
        self.mock_audio_segment_class.from_file.side_effect = FileNotFoundError(
            "WAV not found"
        )
        with pytest.raises(FileNotFoundError):
            backend.convert_to_mp3("nonexistent.wav", self.DUMMY_MP3)

    def test_convert_to_mp3_pydub_encode_error(self, backend: PyAudioBackend) -> None:
        """Test convert_to_mp3 handles pydub encoding errors (e.g., ffmpeg issue)."""
        mock_segment_instance = self.mock_audio_segment_class.from_file(self.DUMMY_WAV)
        original_error_message = "MP3 export failed via pydub"
        mock_segment_instance.export.side_effect = CouldntEncodeError(
            original_error_message
        )

        output_filename = self.DUMMY_MP3

        expected_match = (
            f"MP3 encoding failed for {output_filename}. "
            "This usually means ffmpeg or lame is not installed or not found."
        )
        with pytest.raises(AudioError, match=expected_match) as exc_info:
            backend.convert_to_mp3(self.DUMMY_WAV, output_filename)

        assert exc_info.value.details == original_error_message

    def test_convert_to_mp3_no_conversion_config(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test convert_to_mp3 raises ConfigError if conversion settings are missing."""
        type(mock_config_manager.audio).conversion = PropertyMock(return_value=None)

        mock_audio_settings_no_conv = MagicMock(spec=AudioSettings)
        type(mock_audio_settings_no_conv).conversion = PropertyMock(return_value=None)

        fresh_mock_config = MagicMock(spec=ConfigManager)
        type(fresh_mock_config).audio = PropertyMock(
            return_value=mock_audio_settings_no_conv
        )

        current_backend = PyAudioBackend(fresh_mock_config)

        expected_match = "Audio conversion settings are not configured."
        with pytest.raises(ConfigError, match=expected_match) as exc_info:
            current_backend.convert_to_mp3(self.DUMMY_WAV, self.DUMMY_MP3)

        expected_details = "Ensure 'conversion' section in audio config."
        assert exc_info.value.details == expected_details

    def test_del_closes_stream_and_terminates_pyaudio(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test PyAudioBackend __del__ cleans up PyAudio resources."""
        backend_instance = PyAudioBackend(mock_config_manager)
        backend_instance._initialize_pyaudio()

        pyaudio_mock_instance = backend_instance._pyaudio_instance
        assert pyaudio_mock_instance is not None
        terminate_method_mock = pyaudio_mock_instance.terminate

        mock_stream_fixture = self.mock_pyaudio_instance.open()
        backend_instance._stream = mock_stream_fixture
        assert backend_instance._stream is not None
        backend_instance._stream.is_active.return_value = True

        stop_stream_method_mock = backend_instance._stream.stop_stream
        close_method_mock = backend_instance._stream.close

        del backend_instance

        stop_stream_method_mock.assert_called_once()
        close_method_mock.assert_called_once()
        terminate_method_mock.assert_called_once()

    def test_del_handles_errors_gracefully(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test __del__ handles errors during cleanup without raising."""
        backend_instance = PyAudioBackend(mock_config_manager)
        backend_instance._initialize_pyaudio()

        if backend_instance._pyaudio_instance:
            backend_instance._pyaudio_instance.terminate.side_effect = Exception(
                "Terminate error"
            )

        if backend_instance._pyaudio_instance:
            mock_stream_local = backend_instance._pyaudio_instance.open()
            backend_instance._stream = mock_stream_local
            assert backend_instance._stream is not None
            backend_instance._stream.is_active.return_value = True
            backend_instance._stream.stop_stream.side_effect = Exception(
                "Stream stop error"
            )
            backend_instance._stream.close.side_effect = Exception("Stream close error")
        else:
            backend_instance._stream = MagicMock(spec=self.mock_pyaudio_module.Stream)
            assert backend_instance._stream is not None
            backend_instance._stream.is_active.return_value = True
            backend_instance._stream.stop_stream.side_effect = Exception(
                "Stream stop error"
            )
            backend_instance._stream.close.side_effect = Exception("Stream close error")

        try:
            del backend_instance
        except Exception:
            pytest.fail(
                "PyAudioBackend.__del__ raised an exception during error handling."
            )

    def test_stop_recording_inactive_stream_close_exception(
        self, backend: PyAudioBackend
    ) -> None:
        """Test stop_recording handles exception when closing an inactive stream."""
        mock_inactive_stream = MagicMock(
            spec=self.mock_pyaudio_module._Stream_spec_class
        )
        mock_inactive_stream.is_active.return_value = False
        mock_inactive_stream.close.side_effect = Exception("Inactive close failed")
        backend._stream = mock_inactive_stream
        backend._frames = []  # No frames, so it should try to close

        # Expect no error raised, but logged. Stream should be set to None.
        backend.stop_recording()

        mock_inactive_stream.close.assert_called_once()
        assert backend._stream is None
        self.mock_audio_segment_class.assert_not_called()  # type: ignore

    def test_stop_recording_active_stream_stop_exception(
        self, backend: PyAudioBackend, mock_config_manager: MagicMock
    ) -> None:
        """Test stop_recording handles exception from active stream.stop_stream()."""
        mock_active_stream = self.mock_pyaudio_instance.open()
        backend._stream = mock_active_stream
        backend._stream.is_active.return_value = True
        backend._frames = [b"someadata"]
        backend._current_recording_filename = self.DUMMY_WAV

        backend._stream.stop_stream.side_effect = Exception("Stop stream failed")

        # Error is logged, not raised. WAV saving should still be attempted.
        backend.stop_recording()

        mock_active_stream.stop_stream.assert_called_once()
        mock_active_stream.close.assert_called_once()
        assert backend._stream is None
