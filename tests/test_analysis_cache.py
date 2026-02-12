"""Tests for analysis pipeline caching."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.analysis.cache import CachingAnalysisPipeline
from unrealitytv.cache import CacheConfig
from unrealitytv.models import AnalysisResult, Episode, SkipSegment


class TestCachingAnalysisPipeline:
    """Tests for CachingAnalysisPipeline."""

    @pytest.fixture
    def temp_episode(self, tmp_path: Path) -> Episode:
        """Create temporary episode."""
        video_file = tmp_path / "episode.mp4"
        video_file.write_bytes(b"fake video data")
        return Episode(
            file_path=video_file, show_name="TestShow", season=1, episode=1
        )

    @pytest.fixture
    def cache_config(self, tmp_path: Path) -> CacheConfig:
        """Create cache config with temp directory."""
        return CacheConfig(cache_dir=tmp_path / "cache")

    @pytest.fixture
    def pipeline(self, cache_config: CacheConfig) -> CachingAnalysisPipeline:
        """Create caching analysis pipeline."""
        return CachingAnalysisPipeline(use_cache=True, cache_config=cache_config)

    def test_init_with_cache_enabled(self, cache_config: CacheConfig) -> None:
        """Test initialization with caching enabled."""
        pipeline = CachingAnalysisPipeline(use_cache=True, cache_config=cache_config)

        assert pipeline.use_cache is True
        assert pipeline.cache_manager is not None

    def test_init_with_cache_disabled(self, cache_config: CacheConfig) -> None:
        """Test initialization with caching disabled."""
        pipeline = CachingAnalysisPipeline(
            use_cache=False, cache_config=cache_config
        )

        assert pipeline.use_cache is False

    def test_make_cache_key(
        self, pipeline: CachingAnalysisPipeline, temp_episode: Episode
    ) -> None:
        """Test cache key generation."""
        expected_hash = hashlib.md5(str(temp_episode.file_path).encode()).hexdigest()
        expected_key = f"analysis_{expected_hash}"

        key = pipeline._make_cache_key(temp_episode)

        assert key == expected_key

    def test_make_cache_key_different_episodes(
        self, pipeline: CachingAnalysisPipeline, tmp_path: Path
    ) -> None:
        """Test cache keys differ for different episodes."""
        ep1_file = tmp_path / "ep1.mp4"
        ep2_file = tmp_path / "ep2.mp4"
        ep1_file.write_bytes(b"data1")
        ep2_file.write_bytes(b"data2")

        ep1 = Episode(file_path=ep1_file, show_name="Show")
        ep2 = Episode(file_path=ep2_file, show_name="Show")

        key1 = pipeline._make_cache_key(ep1)
        key2 = pipeline._make_cache_key(ep2)

        assert key1 != key2

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_cache_hit(
        self, mock_super: MagicMock, pipeline: CachingAnalysisPipeline, temp_episode: Episode
    ) -> None:
        """Test cache hit returns cached result without calling analyzer."""
        # Pre-populate cache
        segments = [
            SkipSegment(
                start_ms=0,
                end_ms=5000,
                segment_type="recap",
                confidence=0.9,
                reason="Recap detected",
            )
        ]
        result = AnalysisResult(episode=temp_episode, segments=segments)

        cache_key = pipeline._make_cache_key(temp_episode)
        cache_data = result.model_dump()
        pipeline.cache_manager.set(cache_key, cache_data)

        # Analyze should return cached data
        cached_result = pipeline.analyze(temp_episode)

        assert len(cached_result.segments) == 1
        assert cached_result.segments[0].segment_type == "recap"
        mock_super.assert_not_called()

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_cache_miss(
        self,
        mock_super: MagicMock,
        pipeline: CachingAnalysisPipeline,
        temp_episode: Episode,
    ) -> None:
        """Test cache miss calls parent analyzer and caches result."""
        segments = [
            SkipSegment(
                start_ms=0,
                end_ms=5000,
                segment_type="recap",
                confidence=0.9,
                reason="Recap detected",
            )
        ]
        result = AnalysisResult(episode=temp_episode, segments=segments)
        mock_super.return_value = result

        cached_result = pipeline.analyze(temp_episode)

        assert len(cached_result.segments) == 1
        mock_super.assert_called_once()

        # Verify it was cached
        cache_key = pipeline._make_cache_key(temp_episode)
        cached = pipeline.cache_manager.get(cache_key)
        assert cached is not None

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_cache_disabled(
        self,
        mock_super: MagicMock,
        cache_config: CacheConfig,
        temp_episode: Episode,
    ) -> None:
        """Test analysis with caching disabled."""
        pipeline = CachingAnalysisPipeline(
            use_cache=False, cache_config=cache_config
        )

        segments = [
            SkipSegment(
                start_ms=0,
                end_ms=5000,
                segment_type="recap",
                confidence=0.9,
                reason="Recap detected",
            )
        ]
        result = AnalysisResult(episode=temp_episode, segments=segments)
        mock_super.return_value = result

        cached_result = pipeline.analyze(temp_episode)

        assert len(cached_result.segments) == 1

        # Verify nothing was cached
        cache_key = pipeline._make_cache_key(temp_episode)
        cached = pipeline.cache_manager.get(cache_key)
        assert cached is None

    def test_clear_cache(self, pipeline: CachingAnalysisPipeline, temp_episode: Episode) -> None:
        """Test clearing analysis cache."""
        # Add item to cache
        segments = []
        result = AnalysisResult(episode=temp_episode, segments=segments)
        cache_key = pipeline._make_cache_key(temp_episode)
        cache_data = result.model_dump()
        pipeline.cache_manager.set(cache_key, cache_data)

        assert pipeline.cache_manager.get(cache_key) is not None

        pipeline.clear_cache()

        assert pipeline.cache_manager.get(cache_key) is None

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_multiple_segments(
        self,
        mock_super: MagicMock,
        pipeline: CachingAnalysisPipeline,
        temp_episode: Episode,
    ) -> None:
        """Test analyzing with multiple detected segments."""
        segments = [
            SkipSegment(
                start_ms=0,
                end_ms=5000,
                segment_type="recap",
                confidence=0.9,
                reason="Recap detected",
            ),
            SkipSegment(
                start_ms=40000,
                end_ms=45000,
                segment_type="preview",
                confidence=0.85,
                reason="Preview detected",
            ),
        ]
        result = AnalysisResult(episode=temp_episode, segments=segments)
        mock_super.return_value = result

        cached_result = pipeline.analyze(temp_episode)

        assert len(cached_result.segments) == 2
        assert cached_result.segments[0].segment_type == "recap"
        assert cached_result.segments[1].segment_type == "preview"

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_no_segments(
        self,
        mock_super: MagicMock,
        pipeline: CachingAnalysisPipeline,
        temp_episode: Episode,
    ) -> None:
        """Test analyzing with no detected segments."""
        result = AnalysisResult(episode=temp_episode, segments=[])
        mock_super.return_value = result

        cached_result = pipeline.analyze(temp_episode)

        assert len(cached_result.segments) == 0

        # Verify empty result was cached
        cache_key = pipeline._make_cache_key(temp_episode)
        cached = pipeline.cache_manager.get(cache_key)
        assert cached is not None

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_with_custom_keywords(
        self,
        mock_super: MagicMock,
        cache_config: CacheConfig,
        temp_episode: Episode,
    ) -> None:
        """Test analysis pipeline with custom keywords."""
        pipeline = CachingAnalysisPipeline(
            recap_keywords=["recap", "previously"],
            preview_keywords=["next time", "coming soon"],
            use_cache=True,
            cache_config=cache_config,
        )

        segments = []
        result = AnalysisResult(episode=temp_episode, segments=segments)
        mock_super.return_value = result

        cached_result = pipeline.analyze(temp_episode)

        assert len(cached_result.segments) == 0

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_cache_persistence(
        self,
        mock_super: MagicMock,
        tmp_path: Path,
        temp_episode: Episode,
    ) -> None:
        """Test cache persists across pipeline instances."""
        cache_config = CacheConfig(cache_dir=tmp_path / "cache")
        pipeline1 = CachingAnalysisPipeline(cache_config=cache_config)

        segments = [
            SkipSegment(
                start_ms=0,
                end_ms=5000,
                segment_type="recap",
                confidence=0.9,
                reason="Recap detected",
            )
        ]
        result = AnalysisResult(episode=temp_episode, segments=segments)
        mock_super.return_value = result

        # First pipeline analyzes
        result1 = pipeline1.analyze(temp_episode)
        assert len(result1.segments) == 1

        # Second pipeline with same cache dir should hit cache
        pipeline2 = CachingAnalysisPipeline(cache_config=cache_config)
        result2 = pipeline2.analyze(temp_episode)

        assert len(result2.segments) == 1
        # Parent should only be called once
        assert mock_super.call_count == 1

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_different_episodes_separate_cache(
        self,
        mock_super: MagicMock,
        pipeline: CachingAnalysisPipeline,
        tmp_path: Path,
    ) -> None:
        """Test different episodes have separate cache entries."""
        ep1_file = tmp_path / "ep1.mp4"
        ep2_file = tmp_path / "ep2.mp4"
        ep1_file.write_bytes(b"data1")
        ep2_file.write_bytes(b"data2")

        ep1 = Episode(file_path=ep1_file, show_name="Show")
        ep2 = Episode(file_path=ep2_file, show_name="Show")

        segments1 = [
            SkipSegment(
                start_ms=0,
                end_ms=5000,
                segment_type="recap",
                confidence=0.9,
                reason="Recap",
            )
        ]
        segments2 = [
            SkipSegment(
                start_ms=0,
                end_ms=10000,
                segment_type="preview",
                confidence=0.95,
                reason="Preview",
            )
        ]

        result1 = AnalysisResult(episode=ep1, segments=segments1)
        result2 = AnalysisResult(episode=ep2, segments=segments2)

        mock_super.side_effect = [result1, result2]

        cached_result1 = pipeline.analyze(ep1)
        cached_result2 = pipeline.analyze(ep2)

        assert cached_result1.segments[0].segment_type == "recap"
        assert cached_result2.segments[0].segment_type == "preview"
