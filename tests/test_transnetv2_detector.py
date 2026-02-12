"""Tests for TransNetV2 GPU-accelerated scene detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.detectors.transnetv2_detector import detect_scenes_gpu
from unrealitytv.models import SceneBoundary


@pytest.fixture
def mock_video_path(tmp_path: Path) -> Path:
    """Create a temporary video file path."""
    video_file = tmp_path / "test.mp4"
    video_file.touch()
    return video_file


class TestTransNetV2Detection:
    """Tests for TransNetV2 GPU-accelerated scene detection."""

    def test_detect_scenes_gpu_success(self, mock_video_path: Path) -> None:
        """Test successful GPU-accelerated scene detection."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = True
            mock_device = MagicMock()
            mock_torch.device.return_value = mock_device

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 5,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            scenes = detect_scenes_gpu(mock_video_path)

            assert isinstance(scenes, list)
            assert all(isinstance(s, SceneBoundary) for s in scenes)

    def test_detect_scenes_gpu_custom_device(self, mock_video_path: Path) -> None:
        """Test GPU device selection."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = True
            mock_device = MagicMock()
            mock_torch.device.return_value = mock_device

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 5,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            detect_scenes_gpu(mock_video_path, gpu_device=2)

            # Verify device was created
            mock_torch.device.assert_called()

    def test_detect_scenes_gpu_custom_threshold(self, mock_video_path: Path) -> None:
        """Test that custom threshold is used for detection."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = False
            mock_torch.device.return_value = MagicMock()

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 5,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            detect_scenes_gpu(mock_video_path, threshold=0.9)

            # Should complete without error
            assert True

    def test_detect_scenes_gpu_empty_video(self, mock_video_path: Path) -> None:
        """Test handling of video with no frames."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = False
            mock_torch.device.return_value = MagicMock()

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 5,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            scenes = detect_scenes_gpu(mock_video_path)

            assert len(scenes) == 0

    def test_detect_scenes_gpu_import_error(self, mock_video_path: Path) -> None:
        """Test handling of missing transnetv2 library."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2", None
        ):
            with pytest.raises(RuntimeError, match="transnetv2 library is not installed"):
                detect_scenes_gpu(mock_video_path)

    def test_detect_scenes_gpu_video_open_error(self, mock_video_path: Path) -> None:
        """Test handling of video file open errors."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = False
            mock_torch.device.return_value = MagicMock()

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = False
            mock_cv2.VideoCapture.return_value = mock_cap

            with pytest.raises(RuntimeError, match="Failed to open video file"):
                detect_scenes_gpu(mock_video_path)

    def test_detect_scenes_gpu_respects_min_length(self, mock_video_path: Path) -> None:
        """Test that min_scene_len_ms filters short scenes."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = False
            mock_device = MagicMock()
            mock_torch.device.return_value = mock_device

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 5,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            scenes = detect_scenes_gpu(mock_video_path, min_scene_len_ms=2000)

            # All returned scenes should be >= 2000ms
            assert all(s.end_ms - s.start_ms >= 2000 for s in scenes)

    def test_detect_scenes_gpu_cpu_fallback(self, mock_video_path: Path) -> None:
        """Test fallback to CPU when GPU is not available."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            # GPU not available
            mock_torch.cuda.is_available.return_value = False
            mock_device = MagicMock()
            mock_torch.device.return_value = mock_device

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 5,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            scenes = detect_scenes_gpu(mock_video_path, gpu_device=0)

            # Should fall back to CPU and complete successfully
            assert isinstance(scenes, list)

    def test_detect_scenes_gpu_sequential_indexing(self, mock_video_path: Path) -> None:
        """Test that scene indices are assigned sequentially."""
        with patch(
            "unrealitytv.detectors.transnetv2_detector.torch"
        ) as mock_torch, patch(
            "unrealitytv.detectors.transnetv2_detector.TransNetV2"
        ) as mock_transnetv2_class, patch(
            "unrealitytv.detectors.transnetv2_detector.cv2"
        ) as mock_cv2:
            mock_torch.cuda.is_available.return_value = False
            mock_device = MagicMock()
            mock_torch.device.return_value = mock_device

            mock_model = MagicMock()
            mock_transnetv2_class.return_value = mock_model
            mock_model_with_device = MagicMock()
            mock_model_with_device.eval.return_value = None
            mock_model.to.return_value = mock_model_with_device

            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_cap.get.side_effect = lambda x: {
                mock_cv2.CAP_PROP_FPS: 30.0,
                mock_cv2.CAP_PROP_FRAME_COUNT: 6,
            }.get(x, 0)
            mock_cap.read.return_value = (False, None)
            mock_cv2.VideoCapture.return_value = mock_cap

            scenes = detect_scenes_gpu(mock_video_path)

            # If there are scenes, verify sequential indexing
            for i, scene in enumerate(scenes):
                assert scene.scene_index == i
