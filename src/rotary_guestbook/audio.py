"""Defines the abstract interface for audio backend implementations."""

import abc
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError, CouldntEncodeError

from rotary_guestbook.errors import AudioError, ConfigError

if TYPE_CHECKING:
    import pyaudio

    from rotary_guestbook.config import (
        AudioSettings,
        ConfigManager,
        ConversionSettings,
        RecordingSettings,
    )


logger = logging.getLogger(__name__)


class AbstractAudioBackend(abc.ABC):
    """Abstract base class for audio backend implementations.

    This interface defines the essential operations for audio playback,
    recording, and processing that any concrete audio backend must provide.
    """

    @abc.abstractmethod
    def play_greeting(self) -> None:
        """Play the pre-configured greeting message.

        Raises:
            AudioError: If there is an issue playing the greeting.
        """
        pass

    @abc.abstractmethod
    def start_recording(self, filename: str) -> None:
        """Start recording audio to the specified file.

        Args:
            filename: The name of the file to save the recording to.
                This should be a WAV file initially.

        Raises:
            AudioError: If there is an issue starting the recording.
        """
        pass

    @abc.abstractmethod
    def stop_recording(self) -> None:
        """Stop the current audio recording.

        Raises:
            AudioError: If there is an issue stopping the recording.
        """
        pass

    @abc.abstractmethod
    def convert_to_mp3(self, input_wav: str, output_mp3: str) -> None:
        """Convert a WAV audio file to MP3 format.

        Args:
            input_wav: Path to the input WAV file.
            output_mp3: Path to save the output MP3 file.

        Raises:
            AudioError: If there is an issue during conversion.
            FileNotFoundError: If the input_wav file does not exist.
        """
        pass


class AudioManager:
    """Manages audio operations like playback and recording.

    This class orchestrates audio operations using a configured audio backend.
    It handles playing greetings, managing recording sessions, and converting
    audio formats.
    """

    def __init__(
        self,
        audio_backend: AbstractAudioBackend,
        config_manager: "ConfigManager",
    ) -> None:
        """Initialize AudioManager.

        Args:
            audio_backend: The audio backend to use for operations.
            config_manager: The application configuration manager.
        """
        self._audio_backend = audio_backend
        self._audio_settings: "AudioSettings" = config_manager.audio
        self._is_recording = False
        logger.info("AudioManager initialized.")

    def play_greeting(self) -> None:
        """Plays the greeting message.

        Raises:
            AudioError: If an audio error occurs during playback.
        """
        if not self._audio_settings.greeting_message_path:
            logger.warning(
                "Greeting message path is not configured. Skipping playback."
            )
            return
        logger.info(f"Playing greeting: {self._audio_settings.greeting_message_path}")
        try:
            self._audio_backend.play_greeting()
        except AudioError as e:
            logger.error(f"Error playing greeting: {e.message}", exc_info=True)
            raise
        except Exception as e:
            logger.error("Unexpected error playing greeting", exc_info=True)
            raise AudioError(
                "Failed to play greeting due to an unexpected error.", str(e)
            )

    def start_recording(self, output_filename_base: str) -> None:
        """Start an audio recording.

        Args:
            output_filename_base: The base name for the output recording file
                                  (e.g., "message"). The actual filename will be
                                  timestamped and have a .wav extension.

        Raises:
            AudioError: If an audio error occurs or if already recording.
        """
        if self._is_recording:
            logger.warning("Start recording called while already recording.")
            raise AudioError("Recording is already in progress.")

        wav_filename = f"{output_filename_base}.wav"
        logger.info(f"Starting recording to {wav_filename}")
        try:
            self._audio_backend.start_recording(wav_filename)
            self._is_recording = True
            logger.info("Recording started.")
        except AudioError as e:
            logger.error(f"Error starting recording: {e.message}", exc_info=True)
            raise
        except Exception as e:
            logger.error("Unexpected error starting recording", exc_info=True)
            raise AudioError(
                "Failed to start recording due to an unexpected error.", str(e)
            )

    def stop_recording(self) -> None:
        """Stop the current audio recording.

        Raises:
            AudioError: If an audio error occurs or if not currently recording.
        """
        if not self._is_recording:
            logger.warning("Stop recording called when not recording.")
            raise AudioError("Recording is not in progress.")
        logger.info("Stopping recording.")
        try:
            self._audio_backend.stop_recording()
            self._is_recording = False
            logger.info("Recording stopped.")
        except AudioError as e:
            logger.error(f"Error stopping recording: {e.message}", exc_info=True)
            self._is_recording = False
            raise
        except Exception as e:
            logger.error("Unexpected error stopping recording", exc_info=True)
            self._is_recording = False
            raise AudioError(
                "Failed to stop recording due to an unexpected error.", str(e)
            )

    def convert_to_mp3(self, input_wav: str, output_mp3: str) -> None:
        """Convert a WAV file to MP3 format using the audio backend.

        Args:
            input_wav: Path to the input WAV file.
            output_mp3: Path for the output MP3 file.

        Raises:
            AudioError: If conversion fails.
            FileNotFoundError: If the input WAV file does not exist.
        """
        logger.info(f"Converting {input_wav} to {output_mp3}")
        try:
            self._audio_backend.convert_to_mp3(input_wav, output_mp3)
            logger.info(f"Successfully converted {input_wav} to {output_mp3}")
        except FileNotFoundError:
            logger.error(f"Input WAV file not found for conversion: {input_wav}")
            raise
        except AudioError as e:
            logger.error(
                f"Audio backend error converting {input_wav} to {output_mp3}: "
                f"{e.message}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error converting {input_wav} to {output_mp3}",
                exc_info=True,
            )
            raise AudioError(
                f"Failed to convert {input_wav} to MP3 due to an unexpected error.",
                str(e),
            )

    @property
    def is_recording(self) -> bool:
        """Returns True if audio is currently being recorded, False otherwise."""
        return self._is_recording


class PyAudioBackend(AbstractAudioBackend):
    """Concrete audio backend implementation using PyAudio and Pydub.

    This class handles audio playback, recording using PyAudio, and format
    conversion using Pydub (which can leverage ffmpeg).
    """

    def __init__(self, config_manager: "ConfigManager") -> None:
        """Initialize PyAudioBackend.

        Args:
            config_manager: The application configuration manager.
        """
        self._audio_settings: "AudioSettings" = config_manager.audio
        self._pyaudio_instance: Optional["pyaudio.PyAudio"] = None  # Lazy-loaded
        self._stream: Optional["pyaudio.Stream"] = None  # PyAudio stream
        self._frames: List[bytes] = []
        self._current_recording_filename: Optional[str] = None
        logger.info("PyAudioBackend initialized (PyAudio will be loaded on demand).")

    def _initialize_pyaudio(self) -> None:
        """Initialize PyAudio instance if not already done."""
        if self._pyaudio_instance is None:
            try:
                import pyaudio

                self._pyaudio_instance = pyaudio.PyAudio()
                logger.info("PyAudio imported and instance created successfully.")
            except ImportError:
                logger.error(
                    "PyAudio library not found. Please install it to use "
                    "PyAudioBackend."
                )
                raise AudioError(
                    "PyAudio library not found.",
                    details="Install PyAudio (e.g., 'pip install pyaudio')",
                )
            except Exception as e:
                logger.error("Failed to initialize PyAudio", exc_info=True)
                raise AudioError("Failed to initialize PyAudio.", details=str(e))

    def play_greeting(self) -> None:
        """Play the pre-configured greeting message using pydub and PyAudio."""
        greeting_path = self._audio_settings.greeting_message_path
        if not greeting_path:
            msg = "Greeting message path is not configured."
            logger.error(msg)
            raise ConfigError(msg, details="Ensure 'greeting_message_path' is set.")

        logger.info(f"Attempting to play greeting: {greeting_path}")

        try:
            audio_segment = AudioSegment.from_file(greeting_path)
        except FileNotFoundError:
            logger.error(f"Greeting file not found: {greeting_path}")
            raise AudioError(f"Greeting file not found: {greeting_path}")
        except Exception as e:  # Catches pydub.exceptions.CouldntDecodeError
            logger.error(f"Could not load greeting file {greeting_path}", exc_info=True)
            raise AudioError(f"Could not load greeting file: {greeting_path}", str(e))

        self._initialize_pyaudio()
        assert self._pyaudio_instance is not None

        try:
            pya = self._pyaudio_instance
            pya_format = pya.get_format_from_width(audio_segment.sample_width)
            output_device_idx = self._audio_settings.output_device_index
            self._stream = pya.open(
                format=pya_format,
                channels=audio_segment.channels,
                rate=audio_segment.frame_rate,
                output=True,
                output_device_index=output_device_idx,
            )
            assert self._stream is not None  # Should be opened

            logger.info(f"Playing audio from {greeting_path}...")
            # Actual playback loop
            chunk_size = 1024  # Standard chunk size
            data_chunks = (
                audio_segment.raw_data[i : i + chunk_size]
                for i in range(0, len(audio_segment.raw_data), chunk_size)
            )
            for chunk in data_chunks:
                if not self._stream:
                    logger.warning("Playback stream was closed prematurely.")
                    break
                self._stream.write(chunk)

            logger.info(f"Finished playing {greeting_path}.")

        except Exception as e:  # Catches pyaudio.PaError, OSError etc.
            logger.error("PyAudio error during greeting playback", exc_info=True)
            raise AudioError("Error playing greeting via PyAudio.", str(e))
        finally:
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception as e:
                    logger.error(f"Error closing playback stream: {e}", exc_info=True)
                self._stream = None

    def start_recording(self, filename: str) -> None:
        """Start recording audio to the specified WAV file using PyAudio."""
        logger.debug(f"PyAudioBackend: start_recording called for {filename}")

        if self._stream is not None and self._stream.is_active():
            logger.warning(
                "PyAudioBackend: start_recording called when stream already active."
            )
            raise AudioError(
                "Recording or playback is already in progress",
                details="PyAudio stream is already active.",
            )

        self._initialize_pyaudio()
        assert self._pyaudio_instance is not None

        record_settings: Optional["RecordingSettings"] = self._audio_settings.recording
        if not record_settings:
            msg = "Recording configuration section missing."
            logger.error(msg)
            raise ConfigError(
                msg, details="Ensure 'recording' section in audio config."
            )

        # Assemble log message carefully to avoid long lines
        log_parts = [
            f"Starting PyAudio recording. File: {filename}",
            f"Device: {record_settings.input_device_index or 'default'}",
            f"Ch: {record_settings.channels}",
            f"Rate: {record_settings.rate}",
            f"Chunk: {record_settings.chunk_size}",
            f"Width: {record_settings.sample_width}",
        ]
        logger.info(", ".join(log_parts))
        self._frames = []
        try:
            pya = self._pyaudio_instance
            pya_format = pya.get_format_from_width(record_settings.sample_width)
            self._stream = pya.open(
                format=pya_format,
                channels=record_settings.channels,
                rate=record_settings.rate,
                input=True,
                frames_per_buffer=record_settings.chunk_size,
                input_device_index=record_settings.input_device_index,
                stream_callback=self._recording_callback,
            )
            self._stream.start_stream()
            self._current_recording_filename = filename
            logger.info("PyAudio stream started for recording.")
        except Exception as e:
            logger.error("PyAudio error starting recording", exc_info=True)
            if self._stream is not None:  # Stream was opened but failed later
                try:
                    if self._stream.is_active():
                        self._stream.stop_stream()
                    self._stream.close()
                    logger.info("PyAudio stream closed after error in recording start.")
                except Exception as e_close:
                    logger.warning(
                        "Error closing stream during start_recording exception: "
                        f"{e_close}"
                    )
            self._stream = None  # Ensure stream is marked as None after any failure
            raise AudioError("Error starting recording via PyAudio.", str(e))

    def _recording_callback(
        self,
        in_data: Optional[bytes],
        frame_count: int,
        time_info: Dict[str, float],
        status_flags: int,
    ) -> Tuple[Optional[bytes], int]:
        """Process PyAudio stream callback for recording data."""
        # frame_count, time_info, status_flags are part of PyAudio API,
        # currently unused.
        _ = frame_count, time_info, status_flags  # Mark as unused
        import pyaudio

        if in_data:
            self._frames.append(in_data)
        return (None, pyaudio.paContinue)

    def stop_recording(self) -> None:
        """Stop the current audio recording and save it to a WAV file."""
        if self._stream is None:
            if not self._frames:
                logger.warning(
                    "stop_recording: No stream and no frames. Nothing to do."
                )
                return
            # If stream is None, but there are frames, proceed to save frames.
            # This case might be unusual (e.g. stream failed to open
            # but callback got data?)
            pass  # Fall through to frame saving logic
        else:  # self._stream is not None
            stream = self._stream  # For type narrowing
            if not stream.is_active() and not self._frames:
                logger.warning(
                    "stop_recording: Stream inactive and no frames. Closing stream."
                )
                try:
                    stream.close()
                except Exception as e_close:
                    logger.warning(f"Error closing inactive stream: {e_close}")
                self._stream = None
                return

            logger.info("Stopping PyAudio recording stream.")
            try:
                if stream.is_active():
                    stream.stop_stream()
            except Exception as e_stop_stream:
                # Log the error from stop_stream but continue to try closing
                logger.error(
                    f"Error during stream.stop_stream(): {e_stop_stream}",
                    exc_info=True,
                )
            finally:
                # Always attempt to close the stream
                try:
                    stream.close()
                    logger.info("PyAudio stream closed.")
                except Exception as e_close_stream:
                    logger.error(
                        f"Error during stream.close(): {e_close_stream}",
                        exc_info=True,
                    )
                # Always set self._stream to None after attempting to close
                self._stream = None

        # At this point, self._stream is None. We might have frames.
        if not self._frames:
            logger.warning("No frames recorded, WAV file will not be created.")
            self._current_recording_filename = None
            return

        # If we reach here, self._frames is not empty.
        assert self._frames, "Frames should exist if we are proceeding to save."

        # record_settings will always exist due to Pydantic default_factory
        record_settings = self._audio_settings.recording
        assert record_settings is not None, (
            "Recording settings unexpectedly None in stop_recording. "
            "This should have been caught in start_recording."
        )

        output_filename = self._current_recording_filename
        if not output_filename:
            logger.error("Output filename not set. Cannot save WAV.")
            # Should not happen if logic is correct, but good to guard
            raise AudioError("Internal error: output filename for recording not set.")

        logger.info(f"Saving recorded audio to {output_filename}")
        try:
            audio_segment = AudioSegment(
                data=b"".join(self._frames),
                sample_width=record_settings.sample_width,
                frame_rate=record_settings.rate,
                channels=record_settings.channels,
            )
            audio_segment.export(output_filename, format="wav")
            logger.info(f"Recording saved successfully to {output_filename}")
        except IOError as e:
            logger.error(
                f"IOError saving WAV file {output_filename}: {e}", exc_info=True
            )
            raise AudioError(
                f"Could not save WAV file: {output_filename}", details=str(e)
            )
        except Exception as e:  # Catch-all for other unexpected errors
            logger.error(
                f"Unexpected error saving WAV file {output_filename}: {e}",
                exc_info=True,
            )
            raise AudioError(
                f"Unexpected error saving WAV file: {output_filename}", details=str(e)
            )
        finally:
            # Always clear frames and filename after attempting to save
            self._frames = []
            self._current_recording_filename = None

    def convert_to_mp3(self, input_wav: str, output_mp3: str) -> None:
        """Convert a WAV audio file to MP3 format using Pydub."""
        logger.info(f"Attempting to convert {input_wav} to {output_mp3}")

        conversion_settings: Optional["ConversionSettings"] = (
            self._audio_settings.conversion
        )
        if not conversion_settings:
            msg = "Audio conversion settings are not configured."
            logger.error(msg)
            raise ConfigError(
                msg, details="Ensure 'conversion' section in audio config."
            )

        try:
            audio_segment = AudioSegment.from_file(input_wav)
            logger.debug(f"Successfully loaded {input_wav} for conversion.")
        except FileNotFoundError:
            logger.error(f"Input WAV file not found: {input_wav}")
            # Let FileNotFoundError propagate as per AbstractAudioBackend docstring
            raise
        except CouldntDecodeError as e:
            logger.error(
                f"Could not decode input WAV file {input_wav}: {e}", exc_info=True
            )
            raise AudioError(
                f"Could not decode input WAV file: {input_wav}", details=str(e)
            )
        except Exception as e:  # Catch other loading errors
            logger.error(
                f"Error loading input WAV file {input_wav}: {e}", exc_info=True
            )
            raise AudioError(
                f"Error loading input WAV file: {input_wav}", details=str(e)
            )

        logger.debug(
            f"Converting to MP3: {input_wav} -> {output_mp3}, "
            f"bitrate {conversion_settings.mp3_bitrate}"
        )
        try:
            # Ensure parameters and tags are None if empty, as pydub expects
            export_params = conversion_settings.ffmpeg_parameters or None
            export_tags = getattr(conversion_settings, "id3_tags", None) or None

            audio_segment.export(
                output_mp3,
                format="mp3",
                bitrate=conversion_settings.mp3_bitrate,
                parameters=export_params,
                tags=export_tags,
            )
            logger.info(
                f"Successfully converted {input_wav} to {output_mp3} using pydub."
            )
        except CouldntEncodeError as e:
            logger.error(
                f"Pydub CouldntEncodeError for {output_mp3}. "
                "Ensure ffmpeg/lame is installed and in PATH.",
                exc_info=True,
            )
            raise AudioError(
                f"MP3 encoding failed for {output_mp3}. "
                "This usually means ffmpeg or lame is not installed or not found.",
                details=str(e),
            )
        except IOError as e:  # For filesystem errors during write
            logger.error(f"IOError writing MP3 file {output_mp3}: {e}", exc_info=True)
            raise AudioError(f"Could not write MP3 file: {output_mp3}", details=str(e))
        except Exception as e:  # Catch-all for other pydub export errors
            logger.error(
                f"Unexpected error converting {input_wav} to {output_mp3}: {e}",
                exc_info=True,
            )
            raise AudioError(
                f"Unexpected error converting to MP3: {output_mp3}", details=str(e)
            )

    def __del__(self) -> None:
        """Clean up PyAudio resources when the backend is destroyed."""
        logger.debug("PyAudioBackend __del__ called.")
        if self._stream is not None:
            try:
                stream_to_close = self._stream
                if stream_to_close.is_active():
                    stream_to_close.stop_stream()
                stream_to_close.close()
                logger.info("PyAudio stream closed during PyAudioBackend cleanup.")
            except Exception as e_del_stream:
                logger.warning(
                    f"Error closing stream during PyAudioBackend cleanup: "
                    f"{e_del_stream}"
                )
            self._stream = None

        if self._pyaudio_instance:
            try:
                self._pyaudio_instance.terminate()
                logger.info(
                    "PyAudio instance terminated during PyAudioBackend cleanup."
                )
            except Exception as e_del_pya:
                logger.warning(
                    f"Error terminating PyAudio instance during cleanup: {e_del_pya}"
                )
        self._pyaudio_instance = None


# Placeholder for AudioManager and concrete backend implementation
# which will be added in Phase 3.
# class AudioManager:
#     pass

# class PyAudioBackend(AbstractAudioBackend):
#     pass
