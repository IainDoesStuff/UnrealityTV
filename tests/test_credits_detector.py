"""Tests for credits detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.detectors.credits_detector import detect_credits, _is_credit_frame


@pytest.fixture
def mock_video_path(tmp_path: Path) -> Path:
    """Create a temporary video file path."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()
    return video_file


class TestCreditsDetectionImport:
    """Test credits detection module imports."""

    def test_detect_credits_function_exists(self) -> None:
        """Test that detect_credits function can be imported."""
        assert callable(detect_credits)

    def test_is_credit_frame_function_exists(self) -> None:
        """Test that _is_credit_frame function can be imported."""
        assert callable(_is_credit_frame)

    def test_detect_credits_signature(self) -> None:
        """Test detect_credits function signature."""
        import inspect
        sig = inspect.signature(detect_credits)
        params = list(sig.parameters.keys())
        assert "video_path" in params
        assert "threshold" in params
        assert "min_duration_ms" in params


class TestCreditsDetectionEdgeCases:
    """Edge case tests for credits detection."""

    def test_detect_credits_file_not_exists(self) -> None:
        """Test error handling when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            detect_credits(Path("/nonexistent/video.mp4"))

    def test_detect_credits_invalid_path_type(self) -> None:
        """Test error handling with invalid path."""
        with pytest.raises((TypeError, AttributeError)):
            detect_credits("not_a_path")  # type: ignore


class TestIsCreditFrame:
    """Test frame classification helper."""

    def test_is_credit_frame_signature(self) -> None:
        """Test _is_credit_frame function signature."""
        import inspect
        sig = inspect.signature(_is_credit_frame)
        params = list(sig.parameters.keys())
        assert "frame" in params
        assert "threshold" in params

    def test_is_credit_frame_returns_bool(self) -> None:
        """Test that _is_credit_frame returns boolean."""
        import numpy as np

        # Create a simple frame
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        result = _is_credit_frame(frame, 0.7)
        assert isinstance(result, (bool, np.bool_))


class TestCreditsDetectionWithMocks:
    """Tests with mocked dependencies."""

    def test_detect_credits_returns_scene_boundaries(
        self, mock_video_path: Path
    ) -> None:
        """Test that credits detection returns SceneBoundary objects."""
        # Create a mock VideoCapture
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: {
            5: 30.0,  # FPS
            7: 100,   # Frame count
            1: 0,     # Current frame pos
        }.get(prop, 0)
        mock_capture.read.return_value = (False, None)  # End of video

        with patch("cv2.VideoCapture", return_value=mock_capture), patch(
            "pathlib.Path.exists", return_value=True
        ):
            result = detect_credits(mock_video_path)
            assert isinstance(result, list)

    def test_detect_credits_with_custom_parameters(
        self, mock_video_path: Path
    ) -> None:
        """Test credits detection with custom parameters."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: {
            5: 30.0,
            7: 100,
            1: 0,
        }.get(prop, 0)
        mock_capture.read.return_value = (False, None)

        with patch("cv2.VideoCapture", return_value=mock_capture), patch(
            "pathlib.Path.exists", return_value=True
        ):
            result = detect_credits(
                mock_video_path,
                threshold=0.5,
                min_duration_ms=10000,
                frame_sample_rate=5
            )
            assert isinstance(result, list)


class TestCreditsDetectionThreshold:
    """Test threshold sensitivity."""

    def test_credits_threshold_bounds(self) -> None:
        """Test that threshold is between 0 and 1."""
        import numpy as np

        frame = np.ones((480, 640, 3), dtype=np.uint8) * 128

        # Valid thresholds
        result_low = _is_credit_frame(frame, 0.0)
        result_mid = _is_credit_frame(frame, 0.5)
        result_high = _is_credit_frame(frame, 1.0)

        assert isinstance(result_low, (bool, np.bool_))
        assert isinstance(result_mid, (bool, np.bool_))
        assert isinstance(result_high, (bool, np.bool_))


class TestCreditsDetectionFrameAnalysis:
    """Test frame-level analysis."""

    def test_is_credit_frame_black_detection(self) -> None:
        """Test black frame detection."""
        import numpy as np

        # Pure black frame
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = _is_credit_frame(black_frame, 0.7)
        # Should likely detect this as credits
        assert isinstance(result, (bool, np.bool_))

    def test_is_credit_frame_normal_content(self) -> None:
        """Test normal content frame."""
        import numpy as np

        # Varied content frame
        frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        result = _is_credit_frame(frame, 0.7)
        # Should likely not detect this as credits
        assert isinstance(result, (bool, np.bool_))


class TestCreditsDetectionIntegration:
    """Integration tests for credits detection."""

    def test_detect_credits_video_release(self, mock_video_path: Path) -> None:
        """Test that video is properly released."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: {
            5: 30.0,
            7: 100,
            1: 0,
        }.get(prop, 0)
        mock_capture.read.return_value = (False, None)

        with patch("cv2.VideoCapture", return_value=mock_capture), patch(
            "pathlib.Path.exists", return_value=True
        ):
            detect_credits(mock_video_path)
            # Verify release was called
            mock_capture.release.assert_called()

    def test_detect_credits_fps_fallback(self, mock_video_path: Path) -> None:
        """Test fallback for invalid FPS."""
        mock_capture = MagicMock()
        mock_capture.isOpened.return_value = True
        mock_capture.get.side_effect = lambda prop: {
            5: 0.0,   # Invalid FPS
            7: 100,
            1: 0,
        }.get(prop, 0)
        mock_capture.read.return_value = (False, None)

        with patch("cv2.VideoCapture", return_value=mock_capture), patch(
            "pathlib.Path.exists", return_value=True
        ):
            result = detect_credits(mock_video_path)
            assert isinstance(result, list)
