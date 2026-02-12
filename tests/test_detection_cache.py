"""Tests for scene detection caching."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.cache import CacheConfig
from unrealitytv.detectors.cache import CachingDetectionOrchestrator
from unrealitytv.models import SceneBoundary


class TestCachingDetectionOrchestrator:
    """Tests for CachingDetectionOrchestrator."""

    @pytest.fixture
    def temp_video(self, tmp_path: Path) -> Path:
        """Create temporary video file."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")
        return video_file

    @pytest.fixture
    def cache_config(self, tmp_path: Path) -> CacheConfig:
        """Create cache config with temp directory."""
        return CacheConfig(cache_dir=tmp_path / "cache")

    @pytest.fixture
    def orchestrator(self, cache_config: CacheConfig) -> CachingDetectionOrchestrator:
        """Create caching detection orchestrator."""
        return CachingDetectionOrchestrator(method="auto", use_cache=True, cache_config=cache_config)

    def test_init_with_cache_enabled(self, cache_config: CacheConfig) -> None:
        """Test initialization with caching enabled."""
        orch = CachingDetectionOrchestrator(method="auto", use_cache=True, cache_config=cache_config)

        assert orch.use_cache is True
        assert orch.cache_manager is not None

    def test_init_with_cache_disabled(self, cache_config: CacheConfig) -> None:
        """Test initialization with caching disabled."""
        orch = CachingDetectionOrchestrator(
            method="auto", use_cache=False, cache_config=cache_config
        )

        assert orch.use_cache is False

    def test_make_cache_key(
        self, orchestrator: CachingDetectionOrchestrator, temp_video: Path
    ) -> None:
        """Test cache key generation."""
        method = "scene_detect"
        expected_hash = hashlib.md5(str(temp_video).encode()).hexdigest()
        expected_key = f"detection_{expected_hash}_{method}"

        key = orchestrator._make_cache_key(temp_video, method)

        assert key == expected_key

    def test_make_cache_key_different_methods(
        self, orchestrator: CachingDetectionOrchestrator, temp_video: Path
    ) -> None:
        """Test cache keys differ for different detection methods."""
        key_auto = orchestrator._make_cache_key(temp_video, "auto")
        key_scene = orchestrator._make_cache_key(temp_video, "scene_detect")
        key_transnet = orchestrator._make_cache_key(temp_video, "transnetv2")

        assert key_auto != key_scene
        assert key_scene != key_transnet
        assert "auto" in key_auto
        assert "scene_detect" in key_scene
        assert "transnetv2" in key_transnet

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_cache_hit(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test cache hit returns cached result without calling detector."""
        # Pre-populate cache
        scenes = [
            SceneBoundary(start_ms=0, end_ms=5000, scene_index=0),
            SceneBoundary(start_ms=5000, end_ms=10000, scene_index=1),
        ]

        cache_key = orchestrator._make_cache_key(temp_video, "auto")
        cache_data = [scene.model_dump() for scene in scenes]
        orchestrator.cache_manager.set(cache_key, cache_data)

        # Detect should return cached data
        result = orchestrator.detect_scenes(temp_video)

        assert len(result) == 2
        assert result[0].scene_index == 0
        assert result[1].scene_index == 1
        mock_super.assert_not_called()

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_cache_miss(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test cache miss calls parent detector and caches result."""
        scenes = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        mock_super.return_value = scenes

        result = orchestrator.detect_scenes(temp_video)

        assert len(result) == 1
        mock_super.assert_called_once()

        # Verify it was cached
        cache_key = orchestrator._make_cache_key(temp_video, "auto")
        cached = orchestrator.cache_manager.get(cache_key)
        assert cached is not None

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_with_method(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test detection with specific method."""
        scenes = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        mock_super.return_value = scenes

        result = orchestrator.detect_scenes(temp_video, method="scene_detect")

        assert len(result) == 1
        mock_super.assert_called_once_with(temp_video, "scene_detect")

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_cache_disabled(
        self,
        mock_super: MagicMock,
        cache_config: CacheConfig,
        temp_video: Path,
    ) -> None:
        """Test detection with caching disabled."""
        orch = CachingDetectionOrchestrator(
            method="auto", use_cache=False, cache_config=cache_config
        )

        scenes = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        mock_super.return_value = scenes

        result = orch.detect_scenes(temp_video)

        assert len(result) == 1

        # Verify nothing was cached
        cache_key = orch._make_cache_key(temp_video, "auto")
        cached = orch.cache_manager.get(cache_key)
        assert cached is None

    def test_clear_cache(
        self, orchestrator: CachingDetectionOrchestrator, temp_video: Path
    ) -> None:
        """Test clearing detection cache."""
        # Add item to cache
        cache_key = orchestrator._make_cache_key(temp_video, "auto")
        orchestrator.cache_manager.set(
            cache_key, [{"start_ms": 0, "end_ms": 5000, "scene_index": 0}]
        )

        assert orchestrator.cache_manager.get(cache_key) is not None

        orchestrator.clear_cache()

        assert orchestrator.cache_manager.get(cache_key) is None

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_multiple_scenes(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test detection with many scenes."""
        scenes = [
            SceneBoundary(start_ms=i * 5000, end_ms=(i + 1) * 5000, scene_index=i)
            for i in range(10)
        ]
        mock_super.return_value = scenes

        result = orchestrator.detect_scenes(temp_video)

        assert len(result) == 10
        for i in range(10):
            assert result[i].scene_index == i

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_no_scenes(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test detection with no detected scenes."""
        mock_super.return_value = []

        result = orchestrator.detect_scenes(temp_video)

        assert result == []

        # Verify empty result was cached
        cache_key = orchestrator._make_cache_key(temp_video, "auto")
        cached = orchestrator.cache_manager.get(cache_key)
        assert cached == []

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_method_isolation(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test that different methods have separate cache entries."""
        scenes_scene = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        scenes_transnet = [SceneBoundary(start_ms=0, end_ms=6000, scene_index=0)]

        mock_super.side_effect = [scenes_scene, scenes_transnet]

        # First call with scene_detect
        result_scene = orchestrator.detect_scenes(temp_video, method="scene_detect")
        assert result_scene[0].end_ms == 5000

        # Second call with transnetv2
        result_transnet = orchestrator.detect_scenes(
            temp_video, method="transnetv2"
        )
        assert result_transnet[0].end_ms == 6000

        # Both should have been called
        assert mock_super.call_count == 2

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_with_kwargs(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        temp_video: Path,
    ) -> None:
        """Test detection with additional kwargs."""
        scenes = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        mock_super.return_value = scenes

        result = orchestrator.detect_scenes(
            temp_video, method="scene_detect", threshold=0.5
        )

        assert len(result) == 1
        mock_super.assert_called_once_with(
            temp_video, "scene_detect", threshold=0.5
        )

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_cache_persistence(
        self,
        mock_super: MagicMock,
        tmp_path: Path,
        temp_video: Path,
    ) -> None:
        """Test cache persists across orchestrator instances."""
        cache_config = CacheConfig(cache_dir=tmp_path / "cache")
        orch1 = CachingDetectionOrchestrator(method="auto", cache_config=cache_config)

        scenes = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        mock_super.return_value = scenes

        # First orchestrator detects
        result1 = orch1.detect_scenes(temp_video)
        assert len(result1) == 1

        # Second orchestrator with same cache dir should hit cache
        orch2 = CachingDetectionOrchestrator(method="auto", cache_config=cache_config)
        result2 = orch2.detect_scenes(temp_video)

        assert len(result2) == 1
        # Parent should only be called once
        assert mock_super.call_count == 1

    @patch("unrealitytv.detectors.orchestrator.DetectionOrchestrator.detect_scenes")
    def test_detect_scenes_different_videos_separate_cache(
        self,
        mock_super: MagicMock,
        orchestrator: CachingDetectionOrchestrator,
        tmp_path: Path,
    ) -> None:
        """Test different videos have separate cache entries."""
        vid1 = tmp_path / "vid1.mp4"
        vid2 = tmp_path / "vid2.mp4"
        vid1.write_bytes(b"data1")
        vid2.write_bytes(b"data2")

        scenes1 = [SceneBoundary(start_ms=0, end_ms=5000, scene_index=0)]
        scenes2 = [SceneBoundary(start_ms=0, end_ms=10000, scene_index=0)]

        mock_super.side_effect = [scenes1, scenes2]

        result1 = orchestrator.detect_scenes(vid1)
        result2 = orchestrator.detect_scenes(vid2)

        assert result1[0].end_ms == 5000
        assert result2[0].end_ms == 10000
