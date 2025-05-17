import signal
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from rotary_guestbook.audioInterface import AudioInterface


@pytest.fixture
def audio_interface():
    """Create an AudioInterface instance with test configuration."""
    return AudioInterface(
        alsa_hw_mapping="hw:0,0",
        format="cd",
        file_type="wav",
        recording_limit=30,
        sample_rate=44100,
        channels=1,
        mixer_control_name="Speaker",
    )


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
        mock_run.return_value = MagicMock(returncode=0)
        mock_popen.return_value = MagicMock(
            pid=1234,
            poll=MagicMock(return_value=None),
            wait=MagicMock(return_value=0),
        )
        yield mock_run, mock_popen


def test_init(audio_interface):
    """Test AudioInterface initialization."""
    assert audio_interface.alsa_hw_mapping == "hw:0,0"
    assert audio_interface.format == "cd"
    assert audio_interface.file_type == "wav"
    assert audio_interface.recording_limit == 30
    assert audio_interface.sample_rate == 44100
    assert audio_interface.channels == 1
    assert audio_interface.mixer_control_name == "Speaker"
    assert audio_interface.recording_process is None
    assert audio_interface.playback_process is None
    assert audio_interface.continue_playback is True


def test_set_volume(audio_interface, mock_subprocess):
    """Test volume setting functionality."""
    mock_run, _ = mock_subprocess

    # Test normal volume setting
    audio_interface.set_volume(0.5)
    mock_run.assert_called_once_with(["amixer", "set", "Speaker", "50%"], check=True)

    # Test volume clamping
    mock_run.reset_mock()
    audio_interface.set_volume(1.5)  # Should be clamped to 100%
    mock_run.assert_called_once_with(["amixer", "set", "Speaker", "100%"], check=True)

    # Test volume clamping at 0
    mock_run.reset_mock()
    audio_interface.set_volume(-0.5)  # Should be clamped to 0%
    mock_run.assert_called_once_with(["amixer", "set", "Speaker", "0%"], check=True)


def test_set_volume_error(audio_interface, mock_subprocess):
    """Test volume setting error handling."""
    mock_run, _ = mock_subprocess
    mock_run.side_effect = subprocess.CalledProcessError(1, "amixer")

    # Should not raise exception, just log error
    audio_interface.set_volume(0.5)
    mock_run.assert_called_once_with(["amixer", "set", "Speaker", "50%"], check=True)


def test_play_audio_file_not_found(audio_interface, mock_subprocess):
    """Test playing non-existent audio file."""
    mock_run, _ = mock_subprocess
    audio_interface.play_audio("nonexistent.wav")
    mock_run.assert_not_called()


def test_play_audio_with_delay(audio_interface, mock_subprocess, tmp_path):
    """Test playing audio with start delay."""
    mock_run, mock_popen = mock_subprocess

    # Create a temporary audio file
    test_file = tmp_path / "test.wav"
    test_file.touch()

    # Mock the silence file creation
    mock_run.side_effect = [
        MagicMock(returncode=0),  # sox command
        MagicMock(returncode=0),  # aplay silence
        MagicMock(returncode=0),  # aplay actual file
    ]

    # Make poll() return None once, then 0 to simulate process ending
    mock_popen.return_value.poll.side_effect = [None, 0]

    audio_interface.play_audio(str(test_file), volume=0.8, start_delay_sec=1)

    # Verify silence file was created and played
    assert mock_run.call_count >= 2
    mock_run.assert_any_call(
        [
            "sox",
            "-n",
            "-r",
            "44100",
            "-c",
            "1",
            "/tmp/silence.wav",
            "trim",
            "0",
            "1",
        ],
        check=True,
    )


def test_play_audio_silence_file_error(audio_interface, mock_subprocess, tmp_path):
    """Test error handling when silence file creation fails."""
    mock_run, mock_popen = mock_subprocess

    # Create a temporary audio file
    test_file = tmp_path / "test.wav"
    test_file.touch()

    # Test error in silence file creation
    mock_run.side_effect = subprocess.CalledProcessError(1, "sox")

    # Mock the process to return immediately
    mock_process = MagicMock()
    mock_process.poll.return_value = 0
    mock_popen.return_value = mock_process

    audio_interface.play_audio(str(test_file), start_delay_sec=1)
    assert audio_interface.playback_process is None


def test_play_audio_playback_error(audio_interface, mock_subprocess, tmp_path):
    """Test error handling when playback process fails to start."""
    mock_run, mock_popen = mock_subprocess

    # Create a temporary audio file
    test_file = tmp_path / "test.wav"
    test_file.touch()

    # Test error in playback process creation
    mock_popen.side_effect = subprocess.SubprocessError("Playback failed")
    audio_interface.play_audio(str(test_file))
    assert audio_interface.playback_process is None


def test_stop_playback(audio_interface, mock_subprocess):
    """Test stopping audio playback."""
    mock_run, mock_popen = mock_subprocess
    mock_process = mock_popen.return_value

    # Simulate active playback
    audio_interface.playback_process = mock_process

    audio_interface.stop_playback()

    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once_with(timeout=2)
    assert audio_interface.playback_process is None


def test_stop_playback_force_kill(audio_interface, mock_subprocess):
    """Test force kill in stop_playback when wait times out."""
    mock_run, mock_popen = mock_subprocess
    mock_process = mock_popen.return_value
    audio_interface.playback_process = mock_process
    mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="aplay", timeout=2)
    audio_interface.stop_playback()
    mock_process.kill.assert_called_once()
    assert audio_interface.playback_process is None


def test_start_recording(audio_interface, mock_subprocess, tmp_path):
    """Test starting audio recording."""
    mock_run, mock_popen = mock_subprocess

    # Create test output directory
    output_dir = tmp_path / "recordings"
    output_dir.mkdir()
    output_file = output_dir / "test_recording.wav"

    audio_interface.start_recording(str(output_file))

    # Verify arecord command was called with correct parameters
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert args[0] == "arecord"
    assert args[1] == "-D"
    assert args[2] == "hw:0,0"
    assert args[3] == "-f"
    assert args[4] == "cd"
    assert args[5] == "-t"
    assert args[6] == "wav"
    assert args[7] == "-d"
    assert args[8] == "30"
    assert args[9] == "-r"
    assert args[10] == "44100"
    assert args[11] == "-c"
    assert args[12] == "1"
    assert args[13] == str(output_file)


def test_start_recording_directory_errors(audio_interface, mock_subprocess, tmp_path):
    """Test error handling for directory creation and permissions."""
    mock_run, mock_popen = mock_subprocess

    # Test directory creation error
    with patch("os.makedirs", side_effect=OSError("Permission denied")):
        output_file = tmp_path / "nonexistent" / "test.wav"
        audio_interface.start_recording(str(output_file))
        mock_popen.assert_not_called()

    # Test directory permission error
    with patch("os.access", return_value=False):
        output_file = tmp_path / "test.wav"
        audio_interface.start_recording(str(output_file))
        mock_popen.assert_not_called()


def test_start_recording_oserror(audio_interface, mock_subprocess, tmp_path):
    """Test OSError during directory creation in start_recording."""
    mock_run, mock_popen = mock_subprocess
    with patch("os.makedirs", side_effect=OSError("fail")):
        output_file = tmp_path / "fail" / "test.wav"
        audio_interface.start_recording(str(output_file))
        mock_popen.assert_not_called()


def test_start_recording_subprocess_error(audio_interface, mock_subprocess, tmp_path):
    """Test SubprocessError during Popen in start_recording."""
    mock_run, mock_popen = mock_subprocess
    output_file = tmp_path / "test.wav"
    mock_popen.side_effect = subprocess.SubprocessError("fail")
    audio_interface.start_recording(str(output_file))


def test_stop_recording(audio_interface, mock_subprocess):
    """Test stopping audio recording."""
    mock_run, mock_popen = mock_subprocess
    mock_process = mock_popen.return_value

    # Simulate active recording
    audio_interface.recording_process = mock_process
    mock_process.args = [
        "arecord",
        "-D",
        "hw:0,0",
        "test.wav",
    ]

    with patch("os.killpg") as mock_killpg, patch("os.getpgid", return_value=1234):
        audio_interface.stop_recording()

        # Verify process was terminated
        mock_killpg.assert_called_with(1234, signal.SIGINT)
        mock_process.wait.assert_called_once_with(timeout=2)


def test_stop_recording_timeout_and_escalation(audio_interface, mock_subprocess):
    """Test TimeoutExpired in stop_recording and escalation to SIGTERM/SIGKILL."""
    mock_run, mock_popen = mock_subprocess
    mock_process = mock_popen.return_value
    audio_interface.recording_process = mock_process
    mock_process.args = ["arecord", "-D", "hw:0,0", "test.wav"]
    mock_process.wait.side_effect = [
        subprocess.TimeoutExpired(cmd="arecord", timeout=2),
        None,
    ]
    mock_process.poll.side_effect = [None, None, None, 0]
    with (
        patch("os.killpg") as mock_killpg,
        patch("os.getpgid", return_value=1234),
        patch("time.sleep"),
    ):
        audio_interface.stop_recording()
        assert mock_killpg.call_count >= 2
        assert audio_interface.recording_process is None


def test_stop_recording_processlookup_and_subprocess_error(
    audio_interface, mock_subprocess
):
    """Test ProcessLookupError and SubprocessError in stop_recording."""
    mock_run, mock_popen = mock_subprocess
    mock_process = mock_popen.return_value
    audio_interface.recording_process = mock_process
    mock_process.args = ["arecord", "-D", "hw:0,0", "test.wav"]
    # ProcessLookupError
    with patch("os.killpg", side_effect=ProcessLookupError):
        audio_interface.stop_recording()
    # SubprocessError
    audio_interface.recording_process = mock_process
    with patch("os.killpg", side_effect=subprocess.SubprocessError):
        audio_interface.stop_recording()


def test_stop_recording_final_cleanup(audio_interface, mock_subprocess):
    """Test final cleanup block in stop_recording."""
    mock_run, mock_popen = mock_subprocess
    mock_process = mock_popen.return_value
    audio_interface.recording_process = mock_process
    mock_process.args = ["arecord", "-D", "hw:0,0", "test.wav"]
    with (
        patch("os.killpg"),
        patch("os.getpgid", return_value=1234),
        patch("subprocess.run") as mock_run_sub,
        patch("time.sleep"),
    ):
        mock_run_sub.return_value.returncode = 0
        audio_interface.stop_recording()
        assert mock_run_sub.call_count >= 2
        assert audio_interface.recording_process is None


def test_stop_recording_else_stray_cleanup(audio_interface, mock_subprocess):
    """Test else block in stop_recording for stray process cleanup."""
    mock_run, mock_popen = mock_subprocess
    audio_interface.recording_process = None
    with patch("subprocess.run") as mock_run_sub, patch("time.sleep"):
        mock_run_sub.return_value.returncode = 0
        audio_interface.stop_recording()
        assert mock_run_sub.call_count >= 2


def test_playback_continuation_control(audio_interface, mock_subprocess, tmp_path):
    """Test the continue_playback flag functionality."""
    mock_run, mock_popen = mock_subprocess

    # Create a temporary audio file
    test_file = tmp_path / "test.wav"
    test_file.touch()

    # Create a mock process that will respond to termination
    mock_process = MagicMock()
    # Make poll() return None first, then 0 after termination
    mock_process.poll.side_effect = [None, 0]
    mock_process.terminate.return_value = None
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Set continue_playback to False before starting playback
    audio_interface.continue_playback = False

    # Start playback
    audio_interface.play_audio(str(test_file))

    # Verify the process was terminated
    mock_process.terminate.assert_called_once()
    mock_process.wait.assert_called_once()
    assert audio_interface.playback_process is None
