"""Tests for Phase 8 visual duplicate detection in orchestrator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from unrealitytv.detectors.orchestrator import DetectionOrchestrator
from unrealitytv.models import SkipSegment


@pytest.fixture
def orchestrator():
    """Create a DetectionOrchestrator with visual_duplicates method."""
    return DetectionOrchestrator(method="visual_duplicates")


@pytest.fixture
def temp_video(tmp_path):
    """Create a temporary video file."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()
    return video_file


class TestVisualDuplicatesMethodDispatch:
    """Tests for visual_duplicates method dispatch."""

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_visual_duplicates_dispatch(self, mock_detect, orchestrator, temp_video):
        """Test that visual_duplicates method is dispatched correctly."""
        mock_segment = SkipSegment(
            start_ms=0,
            end_ms=1000,
            segment_type="flashback",
            confidence=0.95,
            reason="test",
        )
        mock_detect.return_value = [mock_segment]

        result = orchestrator.detect_scenes(temp_video)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], SkipSegment)
        mock_detect.assert_called_once()

    def test_unknown_method_raises_error(self, temp_video):
        """Test that unknown method raises ValueError."""
        orch = DetectionOrchestrator(method="unknown_method")

        with pytest.raises(ValueError) as exc_info:
            orch.detect_scenes(temp_video)

        assert "Unknown detection method" in str(exc_info.value)

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_method_kwargs_passed_through(self, mock_detect, orchestrator, temp_video):
        """Test that kwargs are passed through to detector."""
        mock_detect.return_value = []

        orchestrator.detect_scenes(
            temp_video, db="mock_db", episode_id=1, fps=2.0
        )

        # Check that kwargs were passed
        call_kwargs = mock_detect.call_args[1]
        assert call_kwargs["db"] == "mock_db"
        assert call_kwargs["episode_id"] == 1
        assert call_kwargs["fps"] == 2.0

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_logging_on_success(
        self, mock_detect, orchestrator, temp_video, caplog
    ):
        """Test that success is logged."""
        import logging
        caplog.set_level(logging.INFO)
        mock_detect.return_value = []

        orchestrator.detect_scenes(temp_video)

        assert any("Visual duplicate detection" in record.message for record in caplog.records)

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_logging_on_import_error(
        self, mock_detect, orchestrator, temp_video, caplog
    ):
        """Test that import errors are logged and converted."""
        mock_detect.side_effect = ImportError("No imagehash module")

        with pytest.raises(RuntimeError) as exc_info:
            orchestrator.detect_scenes(temp_video)

        assert "imagehash" in str(exc_info.value).lower()
        assert "Pillow" in str(exc_info.value)

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_logging_on_runtime_error(
        self, mock_detect, orchestrator, temp_video, caplog
    ):
        """Test that runtime errors are logged and re-raised."""
        mock_detect.side_effect = RuntimeError("Frame extraction failed")

        with pytest.raises(RuntimeError):
            orchestrator.detect_scenes(temp_video)

        assert "Visual duplicate detection failed" in caplog.text

    def test_orchestrator_with_auto_method_fallback(self):
        """Test that auto method includes visual_duplicates option."""
        orch = DetectionOrchestrator(method="auto")
        # Auto method should work without error
        # (it won't call visual_duplicates unless GPU is available)
        assert orch.method == "auto"

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_empty_result_list(self, mock_detect, orchestrator, temp_video):
        """Test handling of empty result list."""
        mock_detect.return_value = []

        result = orchestrator.detect_scenes(temp_video)

        assert result == []

    @patch("unrealitytv.detectors.visual_duplicate_detector.detect_visual_duplicates")
    def test_multiple_segments_returned(self, mock_detect, orchestrator, temp_video):
        """Test handling of multiple segments."""
        mock_segments = [
            SkipSegment(
                start_ms=0, end_ms=1000, segment_type="flashback", confidence=0.9, reason="test1"
            ),
            SkipSegment(
                start_ms=5000,
                end_ms=6000,
                segment_type="flashback",
                confidence=0.85,
                reason="test2",
            ),
        ]
        mock_detect.return_value = mock_segments

        result = orchestrator.detect_scenes(temp_video)

        assert len(result) == 2
        assert all(isinstance(seg, SkipSegment) for seg in result)
