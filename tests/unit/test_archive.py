"""Unit tests for the archive module.

This module tests the FileSystemStorageBackend and MessageArchiver classes.
"""

import json
import logging

# import os # Unused
# import shutil # Unused
from datetime import datetime
from pathlib import Path

# from typing import Any, Dict, Generator # Unused Dict, Any, Generator
from unittest.mock import MagicMock, mock_open, patch

import pytest

from rotary_guestbook.archive import (
    AbstractStorageBackend,
    ArchiveError,
    FileSystemStorageBackend,
    MessageArchiver,
)
from rotary_guestbook.config import AudioSettings, ConfigManager

# Disable logging for tests to keep output clean
logging.disable(logging.CRITICAL)


@pytest.fixture
def mock_config_manager(tmp_path: Path) -> MagicMock:
    """Fixture to create a mock ConfigManager.

    The mock is configured with a temporary recordings directory.
    """
    mock_audio_settings = MagicMock(spec=AudioSettings)
    mock_audio_settings.output_directory = str(tmp_path / "recordings")

    mock_cm = MagicMock(spec=ConfigManager)
    mock_cm.audio = mock_audio_settings
    return mock_cm


@pytest.fixture
def temp_audio_file(tmp_path: Path) -> Path:
    """Fixture to create a temporary dummy audio file."""
    audio_content = b"dummy audio data"
    file_path = tmp_path / "temp_message_20230101_120000.mp3"
    file_path.write_bytes(audio_content)
    return file_path


class TestFileSystemStorageBackend:
    """Tests for the FileSystemStorageBackend class."""

    def test_initialization_creates_directory(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test that the recordings directory is created on initialization."""
        # storage = FileSystemStorageBackend(mock_config_manager) # Unused variable
        FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        assert recordings_dir.exists()
        assert recordings_dir.is_dir()

    def test_initialization_raises_archive_error_on_creation_failure(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test ArchiveError is raised if directory creation fails."""
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        # Create a file with the same name to cause mkdir to fail
        recordings_dir.touch()
        with pytest.raises(ArchiveError, match="Failed to create recordings directory"):
            FileSystemStorageBackend(mock_config_manager)

    def test_save_message_successful(
        self, mock_config_manager: MagicMock, temp_audio_file: Path
    ) -> None:
        """Test successfully saving a message."""
        storage = FileSystemStorageBackend(mock_config_manager)
        metadata = {
            "filename": temp_audio_file.name,
            "timestamp": datetime.now().isoformat(),
            "duration": 10,
        }
        message_id = storage.save_message(str(temp_audio_file), metadata.copy())

        expected_message_id = temp_audio_file.stem
        assert message_id == expected_message_id

        recordings_dir = Path(mock_config_manager.audio.output_directory)
        expected_audio_path = recordings_dir / temp_audio_file.name
        expected_metadata_path = recordings_dir / f"{expected_message_id}.json"

        assert expected_audio_path.exists()
        assert not temp_audio_file.exists()  # Original moved
        assert expected_metadata_path.exists()

        with open(expected_metadata_path, "r") as f:
            saved_metadata = json.load(f)

        assert saved_metadata["filename"] == temp_audio_file.name
        assert saved_metadata["message_id"] == expected_message_id
        assert saved_metadata["audio_file_path"] == str(expected_audio_path.resolve())
        assert saved_metadata["metadata_file_path"] == str(
            expected_metadata_path.resolve()
        )

    def test_save_message_source_file_not_found(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test FileNotFoundError if source audio file doesn't exist."""
        storage = FileSystemStorageBackend(mock_config_manager)
        with pytest.raises(FileNotFoundError):
            storage.save_message("non_existent_file.mp3", {"filename": "file.mp3"})

    def test_save_message_missing_filename_in_metadata(
        self, mock_config_manager: MagicMock, temp_audio_file: Path
    ) -> None:
        """Test ValueError if metadata is missing 'filename' key."""
        storage = FileSystemStorageBackend(mock_config_manager)
        with pytest.raises(ValueError, match="Metadata must contain a 'filename' key"):
            storage.save_message(str(temp_audio_file), {"some_other_key": "value"})

    @patch("shutil.move")
    def test_save_message_io_error_during_move(
        self,
        mock_move: MagicMock,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test ArchiveError if shutil.move raises IOError."""
        mock_move.side_effect = IOError("Disk full")
        storage = FileSystemStorageBackend(mock_config_manager)
        metadata = {"filename": temp_audio_file.name}
        with pytest.raises(ArchiveError, match="IOError saving message"):
            storage.save_message(str(temp_audio_file), metadata)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_message_io_error_writing_metadata(
        self,
        mock_file_open: MagicMock,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test ArchiveError if opening metadata file for write fails."""
        # Make shutil.move work, but fail on metadata write
        mock_file_open.side_effect = IOError("Permission denied")
        storage = FileSystemStorageBackend(mock_config_manager)
        metadata = {"filename": temp_audio_file.name}

        # Ensure the recordings directory is there for shutil.move to work
        # before mock_open fails
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        recordings_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ArchiveError, match="IOError saving message"):
            storage.save_message(str(temp_audio_file), metadata)

    def test_get_message_successful(
        self, mock_config_manager: MagicMock, temp_audio_file: Path
    ) -> None:
        """Test successfully retrieving a message."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id_stem = temp_audio_file.stem

        # Manually create the files as if saved
        (recordings_dir / temp_audio_file.name).write_bytes(
            temp_audio_file.read_bytes()
        )
        metadata_content = {
            "filename": temp_audio_file.name,
            "message_id": message_id_stem,
            "audio_file_path": str((recordings_dir / temp_audio_file.name).resolve()),
            "test_key": "test_value",
        }
        with open(recordings_dir / f"{message_id_stem}.json", "w") as f:
            json.dump(metadata_content, f)

        result = storage.get_message(message_id_stem)
        assert result is not None
        audio_path, metadata = result
        assert Path(audio_path).name == temp_audio_file.name
        assert metadata["test_key"] == "test_value"
        assert metadata["message_id"] == message_id_stem

    def test_get_message_not_found(self, mock_config_manager: MagicMock) -> None:
        """Test getting a non-existent message returns None."""
        storage = FileSystemStorageBackend(mock_config_manager)
        assert storage.get_message("non_existent_id") is None

    def test_get_message_metadata_corrupt(
        self, mock_config_manager: MagicMock, temp_audio_file: Path
    ) -> None:
        """Test ArchiveError if metadata JSON is corrupt."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id_stem = temp_audio_file.stem

        (recordings_dir / temp_audio_file.name).touch()  # Dummy audio file
        (recordings_dir / f"{message_id_stem}.json").write_text("not valid json")

        with pytest.raises(ArchiveError, match="Error decoding JSON"):
            storage.get_message(message_id_stem)

    def test_get_message_audio_file_missing_from_metadata_path(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test None if audio file path from metadata doesn't exist."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id = "test_audio_missing"

        metadata_content = {
            "filename": "test_audio_missing.mp3",
            "message_id": message_id,
            "audio_file_path": str(recordings_dir / "test_audio_missing.mp3"),
        }
        with open(recordings_dir / f"{message_id}.json", "w") as f:
            json.dump(metadata_content, f)
        # Audio file itself is NOT created

        result = storage.get_message(message_id)
        assert result is None

    def test_list_messages_empty(self, mock_config_manager: MagicMock) -> None:
        """Test listing messages when recordings directory is empty."""
        storage = FileSystemStorageBackend(mock_config_manager)
        assert storage.list_messages() == []

    def test_list_messages_successful(
        self, mock_config_manager: MagicMock, temp_audio_file: Path
    ) -> None:
        """Test listing messages with multiple valid messages."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)

        # Create message 1
        msg1_id = "message1"
        (recordings_dir / f"{msg1_id}.mp3").touch()
        msg1_meta = {
            "message_id": msg1_id,
            "timestamp": "2023-01-01T12:00:00",
            "audio_file_path": str(recordings_dir / f"{msg1_id}.mp3"),
        }
        with open(recordings_dir / f"{msg1_id}.json", "w") as f:
            json.dump(msg1_meta, f)

        # Create message 2 (using temp_audio_file for convenience)
        msg2_id = temp_audio_file.stem
        (recordings_dir / temp_audio_file.name).write_bytes(
            temp_audio_file.read_bytes()
        )
        msg2_meta = {
            "message_id": msg2_id,
            "timestamp": "2023-01-01T13:00:00",
            "audio_file_path": str(recordings_dir / temp_audio_file.name),
        }
        with open(recordings_dir / f"{msg2_id}.json", "w") as f:
            json.dump(msg2_meta, f)

        messages = storage.list_messages()
        assert len(messages) == 2
        # Check sorting by timestamp (descending)
        assert messages[0]["timestamp"] == "2023-01-01T13:00:00"
        assert messages[1]["timestamp"] == "2023-01-01T12:00:00"

    def test_list_messages_skips_corrupt_metadata(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test that corrupt metadata files are skipped during listing."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        (recordings_dir / "corrupt.json").write_text("not json")
        (recordings_dir / "corrupt.mp3").touch()

        # Add a valid message to ensure it's not completely empty
        valid_id = "valid_msg"
        (recordings_dir / f"{valid_id}.mp3").touch()
        valid_meta = {
            "message_id": valid_id,
            "timestamp": "2023-01-02T10:00:00",
            "audio_file_path": str(recordings_dir / f"{valid_id}.mp3"),
        }
        with open(recordings_dir / f"{valid_id}.json", "w") as f:
            json.dump(valid_meta, f)

        messages = storage.list_messages()
        assert len(messages) == 1
        assert messages[0]["message_id"] == valid_id

    def test_list_messages_skips_metadata_with_missing_audio(
        self, mock_config_manager: MagicMock
    ) -> None:
        """Test that metadata is skipped if its audio_file_path does not exist."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)

        # Metadata points to a non-existent audio file
        missing_audio_id = "missing_audio_file"
        meta_content = {
            "message_id": missing_audio_id,
            "timestamp": "2023-01-03T00:00:00",
            "audio_file_path": str(recordings_dir / f"{missing_audio_id}.mp3"),
        }
        with open(recordings_dir / f"{missing_audio_id}.json", "w") as f:
            json.dump(meta_content, f)
        # The actual .mp3 file is not created

        messages = storage.list_messages()
        assert len(messages) == 0

    @patch("pathlib.Path.glob")
    def test_list_messages_os_error_listing_dir(
        self, mock_glob: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test ArchiveError if there's an OSError when globbing files."""
        mock_glob.side_effect = OSError("Permission denied")
        storage = FileSystemStorageBackend(mock_config_manager)
        # Ensure directory exists, so error is from glob
        Path(mock_config_manager.audio.output_directory).mkdir(exist_ok=True)
        with pytest.raises(ArchiveError, match="OSError listing messages"):
            storage.list_messages()

    @patch("json.dump")
    def test_save_message_unexpected_exception(
        self,
        mock_json_dump: MagicMock,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test ArchiveError if an unexpected exception occurs during save_message."""
        mock_json_dump.side_effect = TypeError("Unexpected type error")
        storage = FileSystemStorageBackend(mock_config_manager)
        metadata = {"filename": temp_audio_file.name}
        with pytest.raises(ArchiveError, match="Unexpected error saving message"):
            storage.save_message(str(temp_audio_file), metadata)
        # Ensure cleanup: audio and metadata files should not exist
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id = temp_audio_file.stem
        assert not (recordings_dir / temp_audio_file.name).exists()
        assert not (recordings_dir / f"{message_id}.json").exists()

    def test_get_message_fallback_audio_format(
        self,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test get_message finds .wav file if audio_file_path missing in metadata."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id = "msg_fallback"
        # Create a .wav file
        wav_path = recordings_dir / f"{message_id}.wav"
        wav_path.write_bytes(b"dummy wav data")
        # Metadata without audio_file_path
        meta = {"filename": f"{message_id}.wav", "message_id": message_id}
        with open(recordings_dir / f"{message_id}.json", "w") as f:
            json.dump(meta, f)
        result = storage.get_message(message_id)
        assert result is not None
        audio_path, metadata = result
        assert audio_path.endswith(".wav")
        assert metadata["filename"] == f"{message_id}.wav"

    def test_list_messages_fallback_audio_format(
        self,
        mock_config_manager: MagicMock,
    ) -> None:
        """Test list_messages includes message if .ogg exists and path is missing."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id = "msg_ogg"
        ogg_path = recordings_dir / f"{message_id}.ogg"
        ogg_path.write_bytes(b"dummy ogg data")
        meta = {"filename": f"{message_id}.ogg", "message_id": message_id}
        with open(recordings_dir / f"{message_id}.json", "w") as f:
            json.dump(meta, f)
        messages = storage.list_messages()
        assert any(m["filename"] == f"{message_id}.ogg" for m in messages)

    def test_list_messages_recordings_dir_missing(
        self,
        mock_config_manager: MagicMock,
    ) -> None:
        """Test list_messages returns empty list if recordings folder does not exist."""
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        if recordings_dir.exists():
            for child in recordings_dir.iterdir():
                if child.is_file():
                    child.unlink()
            recordings_dir.rmdir()
        storage = FileSystemStorageBackend(mock_config_manager)
        # Remove the directory after initialization
        recordings_dir.rmdir()
        assert storage.list_messages() == []

    def test_list_messages_sorting_by_timestamp(
        self,
        mock_config_manager: MagicMock,
    ) -> None:
        """Test that list_messages sorts messages by timestamp descending."""
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        # Message 1
        msg1_id = "sort1"
        (recordings_dir / f"{msg1_id}.mp3").touch()
        meta1 = {
            "message_id": msg1_id,
            "timestamp": "2023-01-01T10:00:00",
            "audio_file_path": str(recordings_dir / f"{msg1_id}.mp3"),
        }
        with open(recordings_dir / f"{msg1_id}.json", "w") as f:
            json.dump(meta1, f)
        # Message 2
        msg2_id = "sort2"
        (recordings_dir / f"{msg2_id}.mp3").touch()
        meta2 = {
            "message_id": msg2_id,
            "timestamp": "2023-01-01T12:00:00",
            "audio_file_path": str(recordings_dir / f"{msg2_id}.mp3"),
        }
        with open(recordings_dir / f"{msg2_id}.json", "w") as f:
            json.dump(meta2, f)
        messages = storage.list_messages()
        assert len(messages) == 2
        assert messages[0]["timestamp"] == "2023-01-01T12:00:00"
        assert messages[1]["timestamp"] == "2023-01-01T10:00:00"

    def test_get_message_no_audio_file_found(
        self,
        mock_config_manager: MagicMock,
    ) -> None:
        """
        Test get_message returns None if no audio file is found for any extension.

        This also requires no audio_file_path in metadata.
        """
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id = "no_audio"
        # Metadata without audio_file_path, and no audio files exist
        meta = {
            "filename": f"{message_id}.mp3",
            "message_id": message_id,
        }
        with open(recordings_dir / f"{message_id}.json", "w") as f:
            json.dump(meta, f)
        result = storage.get_message(message_id)
        assert result is None

    def test_get_message_audio_file_path_present_but_missing(
        self,
        mock_config_manager: MagicMock,
    ) -> None:
        """
        Test get_message returns None if audio_file_path is present in metadata.

        This occurs when the file does not exist.
        """
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        message_id = "audio_path_missing"
        meta = {
            "filename": f"{message_id}.mp3",
            "message_id": message_id,
            "audio_file_path": str(recordings_dir / f"{message_id}.mp3"),
        }
        with open(recordings_dir / f"{message_id}.json", "w") as f:
            json.dump(meta, f)
        # Do NOT create the audio file
        result = storage.get_message(message_id)
        assert result is None

    def test_list_messages_sorting_with_missing_timestamps(
        self,
        mock_config_manager: MagicMock,
    ) -> None:
        """
        Test that list_messages sorts messages with and without timestamps.

        Ensures the sort key fallback is exercised.
        """
        storage = FileSystemStorageBackend(mock_config_manager)
        recordings_dir = Path(mock_config_manager.audio.output_directory)
        # Message with timestamp
        msg1_id = "with_timestamp"
        (recordings_dir / f"{msg1_id}.mp3").touch()
        meta1 = {
            "message_id": msg1_id,
            "timestamp": "2023-01-01T10:00:00",
            "audio_file_path": str(recordings_dir / f"{msg1_id}.mp3"),
        }
        with open(recordings_dir / f"{msg1_id}.json", "w") as f:
            json.dump(meta1, f)
        # Message without timestamp
        msg2_id = "no_timestamp"
        (recordings_dir / f"{msg2_id}.mp3").touch()
        meta2 = {
            "message_id": msg2_id,
            "audio_file_path": str(recordings_dir / f"{msg2_id}.mp3"),
        }
        with open(recordings_dir / f"{msg2_id}.json", "w") as f:
            json.dump(meta2, f)
        messages = storage.list_messages()
        # The message with timestamp should come first
        assert messages[0]["message_id"] == msg1_id
        assert messages[1]["message_id"] == msg2_id


@pytest.fixture
def mock_storage_backend() -> MagicMock:
    """Fixture to create a mock AbstractStorageBackend."""
    return MagicMock(spec=AbstractStorageBackend)


class TestMessageArchiver:
    """Tests for the MessageArchiver class."""

    def test_create_unique_filename(
        self, mock_storage_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test unique filename generation."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        filename1 = archiver.create_unique_filename(extension="wav")
        filename2 = archiver.create_unique_filename(extension="wav")
        assert filename1 != filename2
        assert filename1.startswith("message_")
        assert filename1.endswith(".wav")
        assert (
            len(filename1) > len("message_.wav") + 15
        )  # Timestamp YYYYMMDD_HHMMSS_ffffff

    def test_archive_message_successful(
        self,
        mock_storage_backend: MagicMock,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test successfully archiving a message."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        mock_storage_backend.save_message.return_value = "test_message_id"

        extra_meta = {"user_id": "test_user"}
        message_id = archiver.archive_message(
            str(temp_audio_file), audio_format="mp3", extra_metadata=extra_meta
        )

        assert message_id == "test_message_id"
        mock_storage_backend.save_message.assert_called_once()
        called_args, _ = mock_storage_backend.save_message.call_args
        assert called_args[0] == str(temp_audio_file)
        saved_metadata = called_args[1]
        assert saved_metadata["filename"].startswith("message_")
        assert saved_metadata["filename"].endswith(".mp3")
        assert "timestamp" in saved_metadata
        assert saved_metadata["audio_format"] == "mp3"
        assert saved_metadata["size_bytes"] == temp_audio_file.stat().st_size
        assert saved_metadata["user_id"] == "test_user"

    def test_archive_message_file_not_found(
        self, mock_storage_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test ArchiveError if temp audio file doesn't exist."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        with pytest.raises(ArchiveError, match="Audio file not found"):
            archiver.archive_message("non_existent.mp3")

    def test_archive_message_storage_backend_fails(
        self,
        mock_storage_backend: MagicMock,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test ArchiveError if storage backend fails to save."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        mock_storage_backend.save_message.side_effect = ArchiveError("Backend failed")

        with pytest.raises(ArchiveError, match="Backend failed"):
            archiver.archive_message(str(temp_audio_file))

    def test_archive_message_unexpected_error(
        self,
        mock_storage_backend: MagicMock,
        mock_config_manager: MagicMock,
        temp_audio_file: Path,
    ) -> None:
        """Test ArchiveError on unexpected exception during archiving."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        mock_storage_backend.save_message.side_effect = Exception("Something broke")

        with pytest.raises(ArchiveError, match="Failed to archive message"):
            archiver.archive_message(str(temp_audio_file))

    def test_retrieve_message(
        self, mock_storage_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test retrieving a message."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        expected_data = ("path/to/audio.mp3", {"key": "value"})
        mock_storage_backend.get_message.return_value = expected_data

        result = archiver.retrieve_message("some_id")
        assert result == expected_data
        mock_storage_backend.get_message.assert_called_once_with("some_id")

    def test_list_all_messages(
        self, mock_storage_backend: MagicMock, mock_config_manager: MagicMock
    ) -> None:
        """Test listing all messages."""
        archiver = MessageArchiver(mock_storage_backend, mock_config_manager)
        expected_list = [{"msg1": "data1"}, {"msg2": "data2"}]
        mock_storage_backend.list_messages.return_value = expected_list

        result = archiver.list_all_messages()
        assert result == expected_list
        mock_storage_backend.list_messages.assert_called_once()


class TestAbstractStorageBackend:
    """Tests for AbstractStorageBackend instantiation."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that instantiating AbstractStorageBackend raises TypeError."""
        with pytest.raises(TypeError):
            AbstractStorageBackend()
