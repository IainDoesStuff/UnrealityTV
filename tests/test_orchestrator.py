"""Tests for detection orchestrator."""

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


class TestDetectionOrchestrator:
    """Tests for DetectionOrchestrator class."""

    def test_orchestrator_init_default(self) -> None:
        """Test orchestrator initialization with defaults."""
        orchestrator = DetectionOrchestrator()
        assert orchestrator.method == "auto"

    def test_orchestrator_init_scene_detect(self) -> None:
        """Test orchestrator initialization with scene_detect method."""
        orchestrator = DetectionOrchestrator(method="scene_detect")
        assert orchestrator.method == "scene_detect"

    def test_orchestrator_init_transnetv2(self) -> None:
        """Test orchestrator initialization with transnetv2 method."""
        orchestrator = DetectionOrchestrator(method="transnetv2")
        assert orchestrator.method == "transnetv2"

    def test_orchestrator_init_hybrid(self) -> None:
        """Test orchestrator initialization with hybrid method."""
        orchestrator = DetectionOrchestrator(method="hybrid")
        assert orchestrator.method == "hybrid"

    def test_detect_scenes_with_scene_detect(
        self, mock_video_path: Path
    ) -> None:
        """Test detection using PySceneDetect method."""
        with patch(
            "unrealitytv.detectors.scene_detector.detect_scenes"
        ) as mock_detect:
            expected_scenes = [
                SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
                SceneBoundary(start_ms=2000, end_ms=3000, scene_index=1),
            ]
            mock_detect.return_value = expected_scenes

            orchestrator = DetectionOrchestrator(method="scene_detect")
            scenes = orchestrator.detect_scenes(mock_video_path)

            assert len(scenes) == 2
            assert scenes[0].start_ms == 0
            assert scenes[1].start_ms == 2000
            mock_detect.assert_called_once()

    def test_detect_scenes_with_transnetv2(
        self, mock_video_path: Path
    ) -> None:
        """Test detection using TransNetV2 method."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.detect_scenes_gpu"
        ) as mock_detect:
            expected_scenes = [
                SceneBoundary(start_ms=0, end_ms=1500, scene_index=0),
                SceneBoundary(start_ms=2500, end_ms=3500, scene_index=1),
            ]
            mock_detect.return_value = expected_scenes

            orchestrator = DetectionOrchestrator(method="transnetv2")
            scenes = orchestrator.detect_scenes(mock_video_path)

            assert len(scenes) == 2
            assert scenes[0].end_ms == 1500
            mock_detect.assert_called_once()

    def test_detect_scenes_transnetv2_fallback(
        self, mock_video_path: Path
    ) -> None:
        """Test fallback to PySceneDetect when TransNetV2 unavailable."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.detect_scenes_gpu"
        ) as mock_gpu, patch(
            "unrealitytv.detectors.scene_detector.detect_scenes"
        ) as mock_cpu:
            mock_gpu.side_effect = RuntimeError(
                "transnetv2 library is not installed"
            )
            expected_scenes = [
                SceneBoundary(start_ms=0, end_ms=1000, scene_index=0)
            ]
            mock_cpu.return_value = expected_scenes

            orchestrator = DetectionOrchestrator(method="transnetv2")
            scenes = orchestrator.detect_scenes(mock_video_path)

            assert len(scenes) == 1
            assert mock_cpu.called

    def test_detect_scenes_with_hybrid(
        self, mock_video_path: Path
    ) -> None:
        """Test detection using hybrid method."""
        with patch(
            "unrealitytv.detectors.scene_detector.detect_scenes"
        ) as mock_cpu, patch(
            "unrealitytv.detectors.transnetv2_detector.detect_scenes_gpu"
        ) as mock_gpu:
            cpu_scenes = [
                SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
                SceneBoundary(start_ms=2000, end_ms=3000, scene_index=1),
            ]
            gpu_scenes = [
                SceneBoundary(start_ms=500, end_ms=1500, scene_index=0),
                SceneBoundary(start_ms=2500, end_ms=3500, scene_index=1),
            ]
            mock_cpu.return_value = cpu_scenes
            mock_gpu.return_value = gpu_scenes

            orchestrator = DetectionOrchestrator(method="hybrid")
            scenes = orchestrator.detect_scenes(mock_video_path)

            # Should merge overlapping scenes
            assert len(scenes) >= 2
            assert mock_cpu.called
            assert mock_gpu.called

    def test_detect_scenes_with_hybrid_gpu_failure(
        self, mock_video_path: Path
    ) -> None:
        """Test hybrid method when GPU detection fails."""
        with patch(
            "unrealitytv.detectors.scene_detector.detect_scenes"
        ) as mock_cpu, patch(
            "unrealitytv.detectors.transnetv2_detector.detect_scenes_gpu"
        ) as mock_gpu:
            cpu_scenes = [
                SceneBoundary(start_ms=0, end_ms=1000, scene_index=0)
            ]
            mock_cpu.return_value = cpu_scenes
            mock_gpu.side_effect = RuntimeError(
                "transnetv2 library is not installed"
            )

            orchestrator = DetectionOrchestrator(method="hybrid")
            scenes = orchestrator.detect_scenes(mock_video_path)

            # Should return CPU results only
            assert len(scenes) == 1
            assert mock_cpu.called

    def test_detect_scenes_with_auto_select(
        self, mock_video_path: Path
    ) -> None:
        """Test auto-select method defaults to scene_detect."""
        with patch(
            "unrealitytv.detectors.scene_detector.detect_scenes"
        ) as mock_cpu:
            expected_scenes = [
                SceneBoundary(start_ms=0, end_ms=1000, scene_index=0)
            ]
            mock_cpu.return_value = expected_scenes

            orchestrator = DetectionOrchestrator(method="auto")
            scenes = orchestrator.detect_scenes(mock_video_path)

            assert len(scenes) == 1
            assert mock_cpu.called

    def test_detect_scenes_invalid_method(
        self, mock_video_path: Path
    ) -> None:
        """Test error handling for invalid method."""
        orchestrator = DetectionOrchestrator(method="invalid_method")

        with pytest.raises(ValueError, match="Unknown detection method"):
            orchestrator.detect_scenes(mock_video_path)

    def test_merge_scene_lists_empty_first(self) -> None:
        """Test merging with empty first list."""
        scenes2 = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
            SceneBoundary(start_ms=2000, end_ms=3000, scene_index=1),
        ]

        result = DetectionOrchestrator._merge_scene_lists([], scenes2)

        assert len(result) == 2
        assert result[0].start_ms == 0

    def test_merge_scene_lists_empty_second(self) -> None:
        """Test merging with empty second list."""
        scenes1 = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
            SceneBoundary(start_ms=2000, end_ms=3000, scene_index=1),
        ]

        result = DetectionOrchestrator._merge_scene_lists(scenes1, [])

        assert len(result) == 2
        assert result[0].start_ms == 0

    def test_merge_scene_lists_overlapping(self) -> None:
        """Test merging overlapping scenes."""
        scenes1 = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
            SceneBoundary(start_ms=2000, end_ms=3000, scene_index=1),
        ]
        scenes2 = [
            SceneBoundary(start_ms=500, end_ms=1500, scene_index=0),
            SceneBoundary(start_ms=2500, end_ms=3500, scene_index=1),
        ]

        result = DetectionOrchestrator._merge_scene_lists(scenes1, scenes2)

        # Overlapping scenes should be merged
        assert len(result) == 2
        assert result[0].start_ms == 0
        assert result[0].end_ms == 1500
        assert result[1].start_ms == 2000
        assert result[1].end_ms == 3500

    def test_merge_scene_lists_adjacent(self) -> None:
        """Test merging adjacent scenes."""
        scenes1 = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
        ]
        scenes2 = [
            SceneBoundary(start_ms=1050, end_ms=2000, scene_index=0),
        ]

        result = DetectionOrchestrator._merge_scene_lists(scenes1, scenes2)

        # Adjacent scenes (within 100ms) should be merged
        assert len(result) == 1
        assert result[0].start_ms == 0
        assert result[0].end_ms == 2000

    def test_merge_scene_lists_reindexing(self) -> None:
        """Test that merged scenes have correct sequential indices."""
        scenes1 = [
            SceneBoundary(start_ms=0, end_ms=1000, scene_index=0),
            SceneBoundary(start_ms=2000, end_ms=3000, scene_index=1),
        ]
        scenes2 = []

        result = DetectionOrchestrator._merge_scene_lists(scenes1, scenes2)

        # Scene indices should be sequential
        assert result[0].scene_index == 0
        assert result[1].scene_index == 1

    def test_detect_scenes_passes_kwargs(
        self, mock_video_path: Path
    ) -> None:
        """Test that kwargs are passed to detection methods."""
        with patch(
            "unrealitytv.detectors.scene_detector.detect_scenes"
        ) as mock_detect:
            mock_detect.return_value = []

            orchestrator = DetectionOrchestrator(method="scene_detect")
            orchestrator.detect_scenes(mock_video_path, threshold=5.0)

            # Verify kwargs were passed
            call_args = mock_detect.call_args
            assert call_args.kwargs.get("threshold") == 5.0
