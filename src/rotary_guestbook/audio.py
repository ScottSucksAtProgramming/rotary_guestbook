"""Defines the abstract interface for audio backend implementations."""

import abc


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


# Placeholder for AudioManager and concrete backend implementation
# which will be added in Phase 3.
# class AudioManager:
#     pass

# class PyAudioBackend(AbstractAudioBackend):
#     pass
