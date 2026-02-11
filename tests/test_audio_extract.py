"""Tests for audio extraction module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.unrealitytv.audio.extract import (
    AudioExtractionError,
    extract_audio,
    get_duration_ms,
)


@pytest.fixture
def temp_video_file(tmp_path: Path) -> Path:
    """Create a temporary dummy video file."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_text("dummy video data")
    return video_file


@pytest.fixture
def temp_audio_output(tmp_path: Path) -> Path:
    """Create a path for temporary audio output."""
    return tmp_path / "extracted_audio.wav"


class TestExtractAudio:
    """Tests for extract_audio function."""

    @patch("subprocess.run")
    def test_extract_audio_success(
        self, mock_run: MagicMock, temp_video_file: Path, temp_audio_output: Path
    ) -> None:
        """Test successful audio extraction."""
        mock_run.return_value = MagicMock(returncode=0)

        extract_audio(temp_video_file, temp_audio_output)

        # Verify ffmpeg was called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "ffmpeg" in call_args
        assert str(temp_video_file) in call_args
        assert str(temp_audio_output) in call_args
        assert "-ar" in call_args
        assert "16000" in call_args
        assert "-ac" in call_args
        assert "1" in call_args  # Mono

    @patch("subprocess.run")
    def test_extract_audio_ffmpeg_not_installed(
        self, mock_run: MagicMock, temp_video_file: Path, temp_audio_output: Path
    ) -> None:
        """Test error when FFmpeg is not installed."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(AudioExtractionError, match="FFmpeg not installed"):
            extract_audio(temp_video_file, temp_audio_output)

    @patch("subprocess.run")
    def test_extract_audio_invalid_file(
        self, mock_run: MagicMock, temp_video_file: Path, temp_audio_output: Path
    ) -> None:
        """Test error when input file is invalid."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr=b"Invalid video file"
        )

        with pytest.raises(AudioExtractionError, match="FFmpeg failed"):
            extract_audio(temp_video_file, temp_audio_output)

    def test_extract_audio_input_not_exists(self, temp_audio_output: Path) -> None:
        """Test error when input file doesn't exist."""
        nonexistent_file = Path("/nonexistent/video.mp4")

        with pytest.raises(AudioExtractionError, match="Input file does not exist"):
            extract_audio(nonexistent_file, temp_audio_output)

    @patch("subprocess.run")
    def test_extract_audio_creates_output_directory(
        self, mock_run: MagicMock, tmp_path: Path, temp_video_file: Path
    ) -> None:
        """Test that extract_audio creates output directory if it doesn't exist."""
        mock_run.return_value = MagicMock(returncode=0)
        nested_output = tmp_path / "deep" / "nested" / "dir" / "audio.wav"

        extract_audio(temp_video_file, nested_output)

        # Verify directory was created
        assert nested_output.parent.exists()

    @patch("subprocess.run")
    def test_extract_audio_overwrites_existing(
        self, mock_run: MagicMock, temp_video_file: Path, temp_audio_output: Path
    ) -> None:
        """Test that extract_audio overwrites existing output file."""
        # Create existing output file
        temp_audio_output.write_text("existing data")
        mock_run.return_value = MagicMock(returncode=0)

        extract_audio(temp_video_file, temp_audio_output)

        # Verify -y flag was used to overwrite
        call_args = mock_run.call_args[0][0]
        assert "-y" in call_args


class TestGetDuration:
    """Tests for get_duration_ms function."""

    @patch("subprocess.run")
    def test_get_duration_success(
        self, mock_run: MagicMock, temp_video_file: Path
    ) -> None:
        """Test successful duration detection."""
        # Mock ffprobe returning 60.5 seconds
        mock_run.return_value = MagicMock(stdout=b"60.5")

        duration = get_duration_ms(temp_video_file)

        assert duration == 60500  # 60.5 seconds = 60500 ms
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "ffprobe" in call_args

    @patch("subprocess.run")
    def test_get_duration_fractional_seconds(
        self, mock_run: MagicMock, temp_video_file: Path
    ) -> None:
        """Test duration with fractional seconds."""
        mock_run.return_value = MagicMock(stdout=b"90.123")

        duration = get_duration_ms(temp_video_file)

        assert duration == 90123

    @patch("subprocess.run")
    def test_get_duration_ffprobe_not_installed(
        self, mock_run: MagicMock, temp_video_file: Path
    ) -> None:
        """Test error when FFprobe is not installed."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(AudioExtractionError, match="FFprobe not installed"):
            get_duration_ms(temp_video_file)

    @patch("subprocess.run")
    def test_get_duration_invalid_file(
        self, mock_run: MagicMock, temp_video_file: Path
    ) -> None:
        """Test error when file is invalid."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")

        with pytest.raises(AudioExtractionError, match="FFprobe failed"):
            get_duration_ms(temp_video_file)

    @patch("subprocess.run")
    def test_get_duration_timeout(
        self, mock_run: MagicMock, temp_video_file: Path
    ) -> None:
        """Test error when ffprobe times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("ffprobe", 10)

        with pytest.raises(AudioExtractionError, match="Failed to parse duration"):
            get_duration_ms(temp_video_file)

    def test_get_duration_file_not_exists(self) -> None:
        """Test error when file doesn't exist."""
        nonexistent_file = Path("/nonexistent/audio.wav")

        with pytest.raises(AudioExtractionError, match="File does not exist"):
            get_duration_ms(nonexistent_file)

    @patch("subprocess.run")
    def test_get_duration_invalid_output(
        self, mock_run: MagicMock, temp_video_file: Path
    ) -> None:
        """Test error when ffprobe returns invalid output."""
        mock_run.return_value = MagicMock(stdout=b"not_a_number")

        with pytest.raises(AudioExtractionError, match="Failed to parse duration"):
            get_duration_ms(temp_video_file)


class TestAudioExtractionError:
    """Tests for AudioExtractionError exception."""

    def test_audio_extraction_error_is_exception(self) -> None:
        """Test that AudioExtractionError is an Exception."""
        error = AudioExtractionError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_audio_extraction_error_chaining(self) -> None:
        """Test exception chaining with AudioExtractionError."""
        original_error = ValueError("original")
        try:
            raise AudioExtractionError("wrapped") from original_error
        except AudioExtractionError as e:
            assert e.__cause__ is original_error
