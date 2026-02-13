"""Tests for frame extraction module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from unrealitytv.visual.extract_frames import FrameExtractionError, extract_frames


class TestExtractFrames:
    """Test suite for extract_frames function."""

    @pytest.fixture
    def temp_video(self, tmp_path):
        """Create a temporary video file path."""
        return tmp_path / "test_video.mp4"

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create a temporary output directory."""
        return tmp_path / "frames"

    def test_extract_frames_valid_call(self, temp_video, temp_output_dir):
        """Test successful frame extraction with mocked subprocess."""
        temp_video.touch()

        with patch("subprocess.run") as mock_run:
            extract_frames(temp_video, temp_output_dir, fps=1.0)

            # Check that subprocess.run was called with correct arguments
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "ffmpeg"
            assert str(temp_video) in call_args[0][0]
            assert "fps=1.0" in call_args[0][0]
            assert call_args[1]["check"] is True

    def test_extract_frames_missing_input_file(self, temp_output_dir):
        """Test FileNotFoundError when input file doesn't exist."""
        missing_video = Path("/nonexistent/video.mp4")

        with pytest.raises(FileNotFoundError) as exc_info:
            extract_frames(missing_video, temp_output_dir)

        assert "does not exist" in str(exc_info.value)

    def test_extract_frames_missing_ffmpeg(self, temp_video, temp_output_dir):
        """Test FileNotFoundError when FFmpeg is not installed."""
        temp_video.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("ffmpeg not found")

            with pytest.raises(FileNotFoundError) as exc_info:
                extract_frames(temp_video, temp_output_dir)

            assert "FFmpeg not installed" in str(exc_info.value)

    def test_extract_frames_ffmpeg_failure(self, temp_video, temp_output_dir):
        """Test FrameExtractionError when FFmpeg command fails."""
        temp_video.touch()

        with patch("subprocess.run") as mock_run:
            error = subprocess.CalledProcessError(
                1, "ffmpeg", stderr=b"Invalid video format"
            )
            mock_run.side_effect = error

            with pytest.raises(FrameExtractionError) as exc_info:
                extract_frames(temp_video, temp_output_dir)

            assert "FFmpeg failed" in str(exc_info.value)
            assert "Invalid video format" in str(exc_info.value)

    def test_extract_frames_creates_output_directory(self, temp_video, temp_output_dir):
        """Test that output directory is created if it doesn't exist."""
        temp_video.touch()
        assert not temp_output_dir.exists()

        with patch("subprocess.run"):
            extract_frames(temp_video, temp_output_dir)

        assert temp_output_dir.exists()

    def test_timestamp_calculation_fps_1(self, temp_video, temp_output_dir):
        """Test timestamp calculation with fps=1.0."""
        temp_video.touch()
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        # Create mock frame files
        frame_files = [
            temp_output_dir / "frame_000001.jpg",
            temp_output_dir / "frame_000002.jpg",
            temp_output_dir / "frame_000003.jpg",
        ]
        for f in frame_files:
            f.touch()

        with patch("subprocess.run"):
            result = extract_frames(temp_video, temp_output_dir, fps=1.0)

        # With fps=1.0, timestamps should be 0, 1000, 2000
        assert len(result) == 3
        assert result[0][0] == 0  # frame_000001 → index 0 → 0ms
        assert result[1][0] == 1000  # frame_000002 → index 1 → 1000ms
        assert result[2][0] == 2000  # frame_000003 → index 2 → 2000ms

    def test_timestamp_calculation_fps_2(self, temp_video, temp_output_dir):
        """Test timestamp calculation with fps=2.0."""
        temp_video.touch()
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        frame_files = [
            temp_output_dir / "frame_000001.jpg",
            temp_output_dir / "frame_000002.jpg",
        ]
        for f in frame_files:
            f.touch()

        with patch("subprocess.run"):
            result = extract_frames(temp_video, temp_output_dir, fps=2.0)

        # With fps=2.0, timestamps should be 0, 500
        assert len(result) == 2
        assert result[0][0] == 0  # index 0 → 0 / 2.0 * 1000 = 0ms
        assert result[1][0] == 500  # index 1 → 1 / 2.0 * 1000 = 500ms

    def test_frame_sorting_by_timestamp(self, temp_video, temp_output_dir):
        """Test that frames are sorted by timestamp."""
        temp_video.touch()
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        # Create frames in non-sequential order
        frame_files = [
            temp_output_dir / "frame_000003.jpg",
            temp_output_dir / "frame_000001.jpg",
            temp_output_dir / "frame_000002.jpg",
        ]
        for f in frame_files:
            f.touch()

        with patch("subprocess.run"):
            result = extract_frames(temp_video, temp_output_dir, fps=1.0)

        # Should be sorted by timestamp
        assert len(result) == 3
        assert result[0][0] == 0  # frame_000001
        assert result[1][0] == 1000  # frame_000002
        assert result[2][0] == 2000  # frame_000003

    def test_return_type_is_list_of_tuples(self, temp_video, temp_output_dir):
        """Test that return type is list of (int, Path) tuples."""
        temp_video.touch()
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        frame_file = temp_output_dir / "frame_000001.jpg"
        frame_file.touch()

        with patch("subprocess.run"):
            result = extract_frames(temp_video, temp_output_dir)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple)
        assert isinstance(result[0][0], int)
        assert isinstance(result[0][1], Path)

    def test_extract_frames_with_different_fps(self, temp_video, temp_output_dir):
        """Test fps parameter variations."""
        temp_video.touch()
        temp_output_dir.mkdir(parents=True, exist_ok=True)

        frame_file = temp_output_dir / "frame_000001.jpg"
        frame_file.touch()

        with patch("subprocess.run"):
            # Test fps=0.5
            result = extract_frames(temp_video, temp_output_dir, fps=0.5)
            assert result[0][0] == 0  # index 0 → 0 / 0.5 * 1000 = 0ms

            # Test fps=10.0
            result = extract_frames(temp_video, temp_output_dir, fps=10.0)
            assert result[0][0] == 0  # index 0 → 0 / 10.0 * 1000 = 0ms
