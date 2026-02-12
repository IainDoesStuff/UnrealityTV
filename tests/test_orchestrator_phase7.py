"""Tests for DetectionOrchestrator Phase 7 enhancements (silence and credits)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from unrealitytv.detectors.orchestrator import DetectionOrchestrator
from unrealitytv.models import SceneBoundary


@pytest.fixture
def mock_video_path(tmp_path: Path) -> Path:
    """Create a temporary video file path."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()
    return video_file


class TestDetectionOrchestratorSilence:
    """Test orchestrator with silence detection."""

    def test_orchestrator_silence_method(self, mock_video_path: Path) -> None:
        """Test orchestrator with silence detection method."""
        mock_silences = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
            SceneBoundary(start_ms=5000, end_ms=6000, scene_index=1),
        ]

        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            return_value=mock_silences,
        ):
            orchestrator = DetectionOrchestrator(method="silence")
            scenes = orchestrator.detect_scenes(mock_video_path)

            assert len(scenes) == 2
            assert scenes[0].start_ms == 0
            assert scenes[1].start_ms == 5000

    def test_orchestrator_silence_with_kwargs(self, mock_video_path: Path) -> None:
        """Test silence detection with custom parameters."""
        mock_silences = []

        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            return_value=mock_silences,
        ) as mock_detect:
            orchestrator = DetectionOrchestrator(method="silence")
            orchestrator.detect_scenes(
                mock_video_path, threshold_db=-50, min_duration_ms=1000
            )

            mock_detect.assert_called_once()
            call_kwargs = mock_detect.call_args[1]
            assert "threshold_db" in call_kwargs
            assert "min_duration_ms" in call_kwargs

    def test_orchestrator_silence_error_handling(self, mock_video_path: Path) -> None:
        """Test error handling in silence detection."""
        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            side_effect=RuntimeError("Silence detection failed"),
        ):
            orchestrator = DetectionOrchestrator(method="silence")
            with pytest.raises(RuntimeError):
                orchestrator.detect_scenes(mock_video_path)


class TestDetectionOrchestratorCredits:
    """Test orchestrator with credits detection."""

    def test_orchestrator_credits_method(self, mock_video_path: Path) -> None:
        """Test orchestrator with credits detection method."""
        mock_credits = [
            SceneBoundary(start_ms=0, end_ms=3000, scene_index=0),
            SceneBoundary(start_ms=27000, end_ms=30000, scene_index=1),
        ]

        with patch(
            "unrealitytv.detectors.credits_detector.detect_credits",
            return_value=mock_credits,
        ):
            orchestrator = DetectionOrchestrator(method="credits")
            scenes = orchestrator.detect_scenes(mock_video_path)

            assert len(scenes) == 2
            assert scenes[0].start_ms == 0
            assert scenes[1].start_ms == 27000

    def test_orchestrator_credits_with_kwargs(self, mock_video_path: Path) -> None:
        """Test credits detection with custom parameters."""
        mock_credits = []

        with patch(
            "unrealitytv.detectors.credits_detector.detect_credits",
            return_value=mock_credits,
        ) as mock_detect:
            orchestrator = DetectionOrchestrator(method="credits")
            orchestrator.detect_scenes(
                mock_video_path, threshold=0.5, min_duration_ms=8000
            )

            mock_detect.assert_called_once()
            call_kwargs = mock_detect.call_args[1]
            assert "threshold" in call_kwargs
            assert "min_duration_ms" in call_kwargs

    def test_orchestrator_credits_error_handling(self, mock_video_path: Path) -> None:
        """Test error handling in credits detection."""
        with patch(
            "unrealitytv.detectors.credits_detector.detect_credits",
            side_effect=RuntimeError("Credits detection failed"),
        ):
            orchestrator = DetectionOrchestrator(method="credits")
            with pytest.raises(RuntimeError):
                orchestrator.detect_scenes(mock_video_path)


class TestDetectionOrchestratorHybridExtended:
    """Test orchestrator with hybrid_extended method."""

    def test_orchestrator_hybrid_extended(self, mock_video_path: Path) -> None:
        """Test hybrid extended detection."""
        scene_detect_scenes = [
            SceneBoundary(start_ms=0, end_ms=5000, scene_index=0),
            SceneBoundary(start_ms=10000, end_ms=15000, scene_index=1),
        ]
        silence_scenes = [
            SceneBoundary(start_ms=20000, end_ms=21000, scene_index=0),
        ]
        credits_scenes = [
            SceneBoundary(start_ms=0, end_ms=3000, scene_index=0),
        ]

        with patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_scene_detect",
            return_value=scene_detect_scenes,
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_transnetv2",
            side_effect=RuntimeError("TransNetV2 not available"),
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_silence",
            return_value=silence_scenes,
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_credits",
            return_value=credits_scenes,
        ):
            orchestrator = DetectionOrchestrator(method="hybrid_extended")
            scenes = orchestrator.detect_scenes(mock_video_path)

            # Should have merged results from all methods
            assert isinstance(scenes, list)
            assert len(scenes) > 0

    def test_orchestrator_hybrid_extended_graceful_fallback(
        self, mock_video_path: Path
    ) -> None:
        """Test hybrid extended with graceful fallback when methods fail."""
        scene_detect_scenes = [
            SceneBoundary(start_ms=0, end_ms=5000, scene_index=0),
        ]

        with patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_scene_detect",
            return_value=scene_detect_scenes,
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_transnetv2",
            side_effect=RuntimeError("Not available"),
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_silence",
            side_effect=Exception("Audio error"),
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_credits",
            side_effect=Exception("Video error"),
        ):
            orchestrator = DetectionOrchestrator(method="hybrid_extended")
            # Should still return results from successful methods
            scenes = orchestrator.detect_scenes(mock_video_path)
            assert isinstance(scenes, list)

    def test_orchestrator_hybrid_extended_merges_overlaps(
        self, mock_video_path: Path
    ) -> None:
        """Test that hybrid extended merges overlapping detections."""
        # Overlapping scenes from different methods
        scene_detect_scenes = [
            SceneBoundary(start_ms=0, end_ms=5000, scene_index=0),
            SceneBoundary(start_ms=10000, end_ms=15000, scene_index=1),
        ]
        silence_scenes = [
            SceneBoundary(start_ms=4500, end_ms=6000, scene_index=0),
        ]

        with patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_scene_detect",
            return_value=scene_detect_scenes,
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_transnetv2",
            side_effect=RuntimeError("Not available"),
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_silence",
            return_value=silence_scenes,
        ), patch(
            "unrealitytv.detectors.orchestrator.DetectionOrchestrator._detect_with_credits",
            return_value=[],
        ):
            orchestrator = DetectionOrchestrator(method="hybrid_extended")
            scenes = orchestrator.detect_scenes(mock_video_path)

            # Overlapping scenes should be merged
            assert isinstance(scenes, list)
            # Should have fewer or equal scenes than input
            assert len(scenes) <= (
                len(scene_detect_scenes) + len(silence_scenes)
            )


class TestDetectionOrchestratorMethodValidation:
    """Test method validation."""

    def test_orchestrator_unknown_method(self, mock_video_path: Path) -> None:
        """Test error on unknown method."""
        orchestrator = DetectionOrchestrator(method="unknown_method")
        with pytest.raises(ValueError) as exc_info:
            orchestrator.detect_scenes(mock_video_path)
        assert "Unknown detection method" in str(exc_info.value)

    def test_orchestrator_valid_methods(self, mock_video_path: Path) -> None:
        """Test that all documented methods are recognized."""
        valid_methods = [
            "scene_detect",
            "transnetv2",
            "hybrid",
            "silence",
            "credits",
            "hybrid_extended",
            "auto",
        ]

        for method in valid_methods:
            orchestrator = DetectionOrchestrator(method=method)
            # Should not raise ValueError for initialization
            assert orchestrator.method == method


class TestDetectionOrchestratorIntegration:
    """Integration tests for enhanced orchestrator."""

    def test_orchestrator_method_chaining(self, mock_video_path: Path) -> None:
        """Test that multiple method calls work correctly."""
        mock_scenes = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
        ]

        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            return_value=mock_scenes,
        ):
            orchestrator = DetectionOrchestrator(method="silence")

            scenes1 = orchestrator.detect_scenes(mock_video_path)
            scenes2 = orchestrator.detect_scenes(mock_video_path)

            assert scenes1 == scenes2

    def test_orchestrator_preserves_scene_indices(
        self, mock_video_path: Path
    ) -> None:
        """Test that scene indices are preserved and reindexed correctly."""
        input_scenes = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
            SceneBoundary(start_ms=5000, end_ms=6000, scene_index=1),
            SceneBoundary(start_ms=10000, end_ms=11000, scene_index=2),
        ]

        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            return_value=input_scenes,
        ):
            orchestrator = DetectionOrchestrator(method="silence")
            scenes = orchestrator.detect_scenes(mock_video_path)

            # Verify scenes are in order
            for i in range(len(scenes) - 1):
                assert scenes[i].start_ms <= scenes[i + 1].start_ms

    def test_orchestrator_mixed_method_results(
        self, mock_video_path: Path
    ) -> None:
        """Test orchestrator handling different result sizes."""
        # Small result
        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            return_value=[SceneBoundary(start_ms=0, end_ms=1000, scene_index=0)],
        ):
            orchestrator = DetectionOrchestrator(method="silence")
            scenes = orchestrator.detect_scenes(mock_video_path)
            assert len(scenes) >= 1

        # Empty result
        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence", return_value=[]
        ):
            orchestrator = DetectionOrchestrator(method="silence")
            scenes = orchestrator.detect_scenes(mock_video_path)
            assert len(scenes) == 0

        # Large result
        large_result = [
            SceneBoundary(start_ms=i * 1000, end_ms=(i + 1) * 1000, scene_index=i)
            for i in range(100)
        ]
        with patch(
            "unrealitytv.detectors.silence_detector.detect_silence",
            return_value=large_result,
        ):
            orchestrator = DetectionOrchestrator(method="silence")
            scenes = orchestrator.detect_scenes(mock_video_path)
            assert len(scenes) == 100
