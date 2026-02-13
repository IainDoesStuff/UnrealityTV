"""Tests for scene boundary detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.detectors.scene_detector import detect_scenes
from unrealitytv.models import SceneBoundary


class MockTimecode:
    """Mock timecode object for testing."""

    def __init__(self, seconds: float):
        """Initialize mock timecode.

        Args:
            seconds: Time in seconds
        """
        self.seconds = seconds

    def get_seconds(self) -> float:
        """Get time in seconds."""
        return self.seconds

    def __sub__(self, other: MockTimecode) -> MockTimecode:
        """Subtract timecodes."""
        return MockTimecode(self.seconds - other.seconds)


@pytest.fixture
def mock_video_path(tmp_path: Path) -> Path:
    """Create a temporary video file path."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()
    return video_file


class TestSceneDetection:
    """Tests for scene detection."""

    def test_detect_scenes_success(self, mock_video_path: Path) -> None:
        """Test successful scene detection."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            # Setup VideoManager mock
            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            # Setup SceneManager mock with realistic scene list
            mock_sm = MagicMock()
            mock_sm.get_scene_list.return_value = [
                (MockTimecode(10.0), MockTimecode(20.0)),
                (MockTimecode(30.0), MockTimecode(40.0)),
                (MockTimecode(50.0), MockTimecode(60.0)),
            ]
            mock_sm_class.return_value = mock_sm

            scenes = detect_scenes(mock_video_path)

            assert len(scenes) == 3
            assert all(isinstance(s, SceneBoundary) for s in scenes)
            assert scenes[0].start_ms == 10000
            assert scenes[0].end_ms == 20000
            assert scenes[0].scene_index == 0

    def test_detect_scenes_respects_min_length(self, mock_video_path: Path) -> None:
        """Test that min_scene_len_ms filters short scenes."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            mock_sm = MagicMock()
            # Some scenes are shorter than 2000ms (the default min)
            mock_sm.get_scene_list.return_value = [
                (MockTimecode(10.0), MockTimecode(11.0)),  # 1000ms - too short
                (MockTimecode(20.0), MockTimecode(25.0)),  # 5000ms - ok
                (MockTimecode(30.0), MockTimecode(31.0)),  # 1000ms - too short
            ]
            mock_sm_class.return_value = mock_sm

            scenes = detect_scenes(mock_video_path, min_scene_len_ms=2000)

            # Only the middle scene should pass the filter
            assert len(scenes) == 1
            assert scenes[0].start_ms == 20000
            assert scenes[0].end_ms == 25000

    def test_detect_scenes_custom_threshold(self, mock_video_path: Path) -> None:
        """Test that custom threshold is passed to AdaptiveDetector."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ) as mock_detector_class:

            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            mock_sm = MagicMock()
            mock_sm.get_scene_list.return_value = []
            mock_sm_class.return_value = mock_sm

            detect_scenes(mock_video_path, threshold=5.0)

            # Verify AdaptiveDetector was called with correct threshold
            mock_detector_class.assert_called_once_with(adaptive_threshold=5.0)

    def test_detect_scenes_empty_video(self, mock_video_path: Path) -> None:
        """Test handling of video with no scenes detected."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            mock_sm = MagicMock()
            mock_sm.get_scene_list.return_value = []
            mock_sm_class.return_value = mock_sm

            scenes = detect_scenes(mock_video_path)

            assert len(scenes) == 0

    def test_detect_scenes_single_scene(self, mock_video_path: Path) -> None:
        """Test video with single scene."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            mock_sm = MagicMock()
            mock_sm.get_scene_list.return_value = [
                (MockTimecode(0.0), MockTimecode(60.0)),
            ]
            mock_sm_class.return_value = mock_sm

            scenes = detect_scenes(mock_video_path)

            assert len(scenes) == 1
            assert scenes[0].scene_index == 0

    def test_detect_scenes_many_scenes(self, mock_video_path: Path) -> None:
        """Test video with many scenes."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            # Create 50 scenes
            scene_list = [
                (MockTimecode(i * 10.0), MockTimecode((i + 1) * 10.0))
                for i in range(50)
            ]

            mock_sm = MagicMock()
            mock_sm.get_scene_list.return_value = scene_list
            mock_sm_class.return_value = mock_sm

            scenes = detect_scenes(mock_video_path)

            assert len(scenes) == 50

    def test_detect_scenes_import_error(self, mock_video_path: Path) -> None:
        """Test handling of missing scenedetect library."""
        with patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector", None
        ):
            with pytest.raises(RuntimeError, match="scenedetect library is not installed"):
                detect_scenes(mock_video_path)

    def test_detect_scenes_video_processing_error(
        self, mock_video_path: Path
    ) -> None:
        """Test handling of video processing errors."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            mock_vm = MagicMock()
            mock_vm.start.side_effect = RuntimeError("Video processing failed")
            mock_vm_class.return_value = mock_vm

            mock_sm = MagicMock()
            mock_sm_class.return_value = mock_sm

            with pytest.raises(RuntimeError, match="Error detecting scenes"):
                detect_scenes(mock_video_path)

    def test_scene_indices_are_sequential(self, mock_video_path: Path) -> None:
        """Test that scene indices are assigned sequentially."""
        with patch(
            "unrealitytv.detectors.scene_detector.VideoManager"
        ) as mock_vm_class, patch(
            "unrealitytv.detectors.scene_detector.SceneManager"
        ) as mock_sm_class, patch(
            "unrealitytv.detectors.scene_detector.AdaptiveDetector"
        ):

            mock_vm = MagicMock()
            mock_vm.get_base_timecode.return_value = MockTimecode(0)
            mock_vm_class.return_value = mock_vm

            mock_sm = MagicMock()
            mock_sm.get_scene_list.return_value = [
                (MockTimecode(0.0), MockTimecode(10.0)),
                (MockTimecode(10.0), MockTimecode(20.0)),
                (MockTimecode(20.0), MockTimecode(30.0)),
            ]
            mock_sm_class.return_value = mock_sm

            scenes = detect_scenes(mock_video_path)

            for i, scene in enumerate(scenes):
                assert scene.scene_index == i
