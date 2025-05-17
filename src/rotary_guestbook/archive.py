"""Defines the abstract interface for message storage backends."""

import abc
from typing import Any, Dict, List, Optional, Tuple


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


# Placeholder for MessageArchiver and concrete backend implementation
# which will be added in Phase 3.
# class MessageArchiver:
#     pass

# class FileSystemStorageBackend(AbstractStorageBackend):
#     pass
