"""Defines the abstract interface for message storage backends."""

import abc
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rotary_guestbook.config import ConfigManager
from rotary_guestbook.errors import ArchiveError

logger = logging.getLogger(__name__)


class AbstractStorageBackend(abc.ABC):
    """Abstract base class for storage backend implementations.

    This interface defines the essential operations for saving, retrieving,
    and listing audio messages and their associated metadata.
    """

    @abc.abstractmethod
    def save_message(self, audio_file_path: str, metadata: Dict[str, Any]) -> str:
        """Save an audio message and its metadata.

        Args:
            audio_file_path: The path to the audio file to be saved.
            metadata: A dictionary containing metadata associated with the message
                      (e.g., timestamp, duration).

        Returns:
            A unique identifier (e.g., file path or database ID) for the
            saved message.

        Raises:
            ArchiveError: If there is an issue saving the message.
            FileNotFoundError: If the audio_file_path does not exist.
        """
        pass

    @abc.abstractmethod
    def get_message(self, message_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Retrieve an audio message and its metadata by its ID.

        Args:
            message_id: The unique identifier of the message to retrieve.

        Returns:
            A tuple containing the audio file path and its metadata dictionary,
            or None if the message is not found.

        Raises:
            ArchiveError: If there is an issue retrieving the message.
        """
        pass

    @abc.abstractmethod
    def list_messages(self) -> List[Dict[str, Any]]:
        """List all available messages with their metadata.

        Returns:
            A list of dictionaries, where each dictionary represents the
            metadata of a message.

        Raises:
            ArchiveError: If there is an issue listing the messages.
        """
        pass


class FileSystemStorageBackend(AbstractStorageBackend):
    """Concrete storage backend that saves messages to the local filesystem.

    Messages are stored as audio files (e.g., MP3) with accompanying
    JSON metadata files in a specified recordings directory.
    """

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the FileSystemStorageBackend.

        Args:
            config_manager: The application's configuration manager.
        """
        self._config_manager = config_manager
        self._recordings_dir = Path(self._config_manager.audio.output_directory)
        self._ensure_recordings_dir_exists()

    def _ensure_recordings_dir_exists(self) -> None:
        """Ensure the recordings directory exists, creating it if necessary."""
        try:
            self._recordings_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Recordings directory set to: {self._recordings_dir.resolve()}"
            )
        except OSError as e:
            msg = f"Failed to create recordings directory: {self._recordings_dir}"
            logger.error(f"{msg} - {e}")
            raise ArchiveError(msg, details=str(e)) from e

    def _get_metadata_path(self, message_id: str) -> Path:
        """Get the path to the metadata file for a given message ID."""
        return self._recordings_dir / f"{message_id}.json"

    def _get_audio_path(self, message_id: str, audio_format: str = "mp3") -> Path:
        """Get the path to the audio file for a given message ID."""
        return self._recordings_dir / f"{message_id}.{audio_format}"

    def save_message(self, audio_file_path: str, metadata: Dict[str, Any]) -> str:
        """Save an audio message and its metadata to the filesystem.

        The message ID is typically the filename without the extension.
        Audio files are moved to the recordings directory, and metadata is
        saved as a JSON file.

        Args:
            audio_file_path: The path to the temporary audio file to be saved.
            metadata: A dictionary containing metadata associated with the message.
                      It's expected to contain at least 'filename'
                      (e.g., 'message_timestamp.mp3').

        Returns:
            The message ID (filename without extension) for the saved message.

        Raises:
            ArchiveError: If there is an issue saving the message or metadata.
            FileNotFoundError: If the audio_file_path does not exist.
            ValueError: If metadata is missing the 'filename' key.
        """
        source_audio_path = Path(audio_file_path)
        if not source_audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        original_filename = metadata.get("filename")
        if not original_filename:
            raise ValueError("Metadata must contain a 'filename' key.")

        message_id = Path(original_filename).stem
        audio_format = Path(original_filename).suffix.lstrip(".")

        destination_audio_path = self._get_audio_path(message_id, audio_format)
        metadata_path = self._get_metadata_path(message_id)

        try:
            self._ensure_recordings_dir_exists()  # Ensure dir exists before writing
            shutil.move(str(source_audio_path), str(destination_audio_path))
            logger.info(f"Moved audio file to: {destination_audio_path}")

            # Add or update paths in metadata
            metadata["audio_file_path"] = str(destination_audio_path.resolve())
            metadata["metadata_file_path"] = str(metadata_path.resolve())
            metadata["message_id"] = message_id

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            logger.info(f"Saved metadata to: {metadata_path}")

        except IOError as e:
            msg = f"IOError saving message {message_id}"
            logger.error(f"{msg}: {e}")
            # Attempt to clean up if one part failed
            if destination_audio_path.exists():
                destination_audio_path.unlink(missing_ok=True)
            if metadata_path.exists():
                metadata_path.unlink(missing_ok=True)
            raise ArchiveError(msg, details=str(e)) from e
        except Exception as e:
            msg = f"Unexpected error saving message {message_id}"
            logger.error(f"{msg}: {e}")
            if destination_audio_path.exists():
                destination_audio_path.unlink(missing_ok=True)
            if metadata_path.exists():
                metadata_path.unlink(missing_ok=True)
            raise ArchiveError(msg, details=str(e)) from e

        return message_id

    def get_message(self, message_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Retrieve an audio message and its metadata by its ID.

        Args:
            message_id: The unique identifier of the message (filename without ext).

        Returns:
            A tuple containing the absolute audio file path and its metadata
            dictionary, or None if the message or its metadata is not found.

        Raises:
            ArchiveError: If there is an issue reading the metadata file.
        """
        metadata_path = self._get_metadata_path(message_id)

        if not metadata_path.exists():
            logger.warning(f"Metadata file not found for message_id: {message_id}")
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Error decoding JSON for metadata file: {metadata_path}"
            logger.error(f"{msg} - {e}")
            raise ArchiveError(msg, details=str(e)) from e
        except IOError as e:
            msg = f"IOError reading metadata file: {metadata_path}"
            logger.error(f"{msg} - {e}")
            raise ArchiveError(msg, details=str(e)) from e

        # Infer audio path from metadata or construct it
        audio_file_path_str = metadata.get("audio_file_path")
        if audio_file_path_str:
            audio_file_path = Path(audio_file_path_str)
        else:
            # Fallback: try to find common audio formats if path not in metadata
            # This part might be removed if 'audio_file_path' is guaranteed in metadata
            found_audio_path = None
            for ext in ["mp3", "wav", "ogg"]:  # Common formats
                potential_path = self._get_audio_path(message_id, ext)
                if potential_path.exists():
                    found_audio_path = potential_path
                    break
            if not found_audio_path:
                logger.warning(
                    f"Audio file for {message_id} not found, and "
                    f"'audio_file_path' missing in {metadata_path.name}"
                )
                return None
            audio_file_path = found_audio_path

        if not audio_file_path.exists():
            logger.warning(
                f"Audio file specified in metadata not found: {audio_file_path}"
            )
            return None

        return str(audio_file_path.resolve()), metadata

    def list_messages(self) -> List[Dict[str, Any]]:
        """List all available messages by reading their metadata files.

        Returns:
            A list of dictionaries, where each dictionary represents the
            metadata of a message. Messages with missing or corrupt metadata
            are skipped.

        Raises:
            ArchiveError: If there is an issue accessing the recordings directory.
        """
        messages: List[Dict[str, Any]] = []
        if not self._recordings_dir.exists():
            logger.warning(
                f"Recordings directory {self._recordings_dir} not found. "
                "Returning empty message list."
            )
            return []

        try:
            for metadata_file in self._recordings_dir.glob("*.json"):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    # Ensure the corresponding audio file exists (optional check)
                    audio_path_str = metadata.get("audio_file_path")
                    if audio_path_str and Path(audio_path_str).exists():
                        messages.append(metadata)
                    elif not audio_path_str:
                        # Try to infer based on message_id if audio_file_path is missing
                        message_id = metadata.get("message_id", metadata_file.stem)
                        found_audio = False
                        for ext in ["mp3", "wav", "ogg"]:
                            path_to_check = self._get_audio_path(message_id, ext)
                            if path_to_check.exists():
                                messages.append(metadata)
                                found_audio = True
                                break
                        if not found_audio:
                            logger.warning(
                                f"Metadata {metadata_file.name} lists no "
                                f"audio_file_path "
                                f"and no audio found for ID {message_id}. "
                                f"Skipping."
                            )
                    else:
                        logger.warning(
                            f"Audio file {audio_path_str} listed in "
                            f"{metadata_file.name} not found. Skipping."
                        )
                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to decode JSON from {metadata_file.name}: {e}. "
                        f"Skipping."
                    )
                except IOError as e:
                    logger.error(
                        f"IOError reading {metadata_file.name}: {e}. Skipping."
                    )
        except OSError as e:
            msg = f"OSError listing messages in {self._recordings_dir}"
            logger.error(f"{msg}: {e}")
            raise ArchiveError(msg, details=str(e)) from e

        # Sort messages, e.g., by timestamp if available in metadata
        messages.sort(
            key=lambda m: m.get("timestamp", ""), reverse=True
        )  # Assuming 'timestamp' key
        return messages


class MessageArchiver:
    """Manages the archiving of audio messages using a storage backend.

    This class acts as an intermediary between the application logic
    and the storage backend, handling tasks like metadata generation
    and filename conventions.
    """

    def __init__(
        self, storage_backend: AbstractStorageBackend, config_manager: ConfigManager
    ) -> None:
        """Initialize the MessageArchiver.

        Args:
            storage_backend: An instance of a class that implements
                             AbstractStorageBackend.
            config_manager: The application's configuration manager.
        """
        self._storage_backend = storage_backend
        self._config_manager = config_manager  # May be used for future configs

    def create_unique_filename(self, extension: str = "mp3") -> str:
        """Generate a unique filename based on the current timestamp.

        Args:
            extension: The file extension (e.g., "mp3", "wav").

        Returns:
            A unique filename string (e.g., "message_20231027_143000.mp3").
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Added microseconds
        return f"message_{timestamp}.{extension}"

    def archive_message(
        self,
        temp_audio_path: str,
        audio_format: str = "mp3",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Archive a new message.

        Generates metadata, creates a unique filename, and uses the storage
        backend to save the message.

        Args:
            temp_audio_path: The path to the temporary audio file to be archived.
            audio_format: The desired audio format for the archived message
                (e.g., "mp3").
            extra_metadata: Optional dictionary with additional metadata to save.

        Returns:
            The message ID of the archived message.

        Raises:
            ArchiveError: If any error occurs during the archiving process.
        """
        try:
            temp_file = Path(temp_audio_path)
            if not temp_file.exists():
                raise ArchiveError(f"Audio file not found: {temp_audio_path}")

            unique_filename = self.create_unique_filename(extension=audio_format)
            timestamp = datetime.now().isoformat()
            file_size = temp_file.stat().st_size

            metadata: Dict[str, Any] = {
                "filename": unique_filename,
                "timestamp": timestamp,
                "audio_format": audio_format,
                "size_bytes": file_size,
                # Potentially add duration later if easily available
            }
            if extra_metadata:
                metadata.update(extra_metadata)

            logger.info(
                f"Archiving message from {temp_audio_path} as {unique_filename}"
            )
            message_id = self._storage_backend.save_message(temp_audio_path, metadata)
            logger.info(
                f"Successfully archived message. Path: {temp_audio_path}, "
                f"ID: {message_id}"
            )
            return message_id
        except ArchiveError:  # Re-raise if it's already an ArchiveError
            raise
        except Exception as e:
            logger.error(f"Failed to archive message from {temp_audio_path}: {e}")
            raise ArchiveError(
                f"Failed to archive message from {temp_audio_path}", details=str(e)
            ) from e

    def retrieve_message(self, message_id: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Retrieve a message by its ID using the storage backend.

        Args:
            message_id: The ID of the message to retrieve.

        Returns:
            A tuple containing the audio file path and its metadata, or None
            if not found.
        """
        logger.debug(f"Attempting to retrieve message with ID: {message_id}")
        return self._storage_backend.get_message(message_id)

    def list_all_messages(self) -> List[Dict[str, Any]]:
        """List all messages available in the storage backend.

        Returns:
            A list of metadata dictionaries for all messages.
        """
        logger.debug("Listing all messages.")
        return self._storage_backend.list_messages()
