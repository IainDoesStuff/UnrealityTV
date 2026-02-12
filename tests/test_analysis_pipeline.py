"""Tests for analysis pipeline that orchestrates the full processing workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from unrealitytv.analysis.pipeline import AnalysisPipeline, AnalysisPipelineError
from unrealitytv.models import AnalysisResult, Episode, SkipSegment
from unrealitytv.transcription.whisper import TranscriptSegment


@pytest.fixture
def valid_episode(tmp_path: Path) -> Episode:
    """Create a valid episode with a temporary video file."""
    video_file = tmp_path / "test_episode.mp4"
    video_file.write_bytes(b"fake video content")
    return Episode(
        file_path=video_file,
        show_name="Test Show",
        season=1,
        episode=1,
        duration_ms=None,
    )


@pytest.fixture
def sample_transcript() -> list[TranscriptSegment]:
    """Create a sample transcript."""
    return [
        TranscriptSegment(start_time_ms=0, end_time_ms=3000, text="Previously..."),
        TranscriptSegment(start_time_ms=3000, end_time_ms=6000, text="Main content"),
    ]


@pytest.fixture
def sample_skip_segments() -> list[SkipSegment]:
    """Create sample skip segments."""
    return [
        SkipSegment(
            start_ms=0,
            end_ms=3000,
            segment_type="recap",
            confidence=0.95,
            reason="Detected: previously",
        ),
    ]


@pytest.fixture
def sample_analysis_result(valid_episode: Episode, sample_skip_segments: list[SkipSegment]) -> AnalysisResult:
    """Create a sample analysis result."""
    return AnalysisResult(episode=valid_episode, segments=sample_skip_segments)


class TestAnalysisPipelineInitialization:
    """Tests for AnalysisPipeline initialization."""

    def test_pipeline_initialization(self) -> None:
        """Test pipeline can be initialized."""
        pipeline = AnalysisPipeline(gpu_enabled=False)
        assert pipeline.gpu_enabled is False
        assert pipeline._transcriber is None
        assert pipeline._matcher is None

    def test_pipeline_with_gpu(self) -> None:
        """Test pipeline initialization with GPU."""
        pipeline = AnalysisPipeline(gpu_enabled=True)
        assert pipeline.gpu_enabled is True

    def test_pipeline_with_custom_keywords(self) -> None:
        """Test pipeline with custom keywords."""
        recap_kw = ["custom_recap"]
        preview_kw = ["custom_preview"]
        pipeline = AnalysisPipeline(
            recap_keywords=recap_kw,
            preview_keywords=preview_kw,
        )
        assert pipeline.recap_keywords == recap_kw
        assert pipeline.preview_keywords == preview_kw


class TestAnalysisPipelineErrorHandling:
    """Tests for error handling."""

    def test_missing_video_file(self, tmp_path: Path) -> None:
        """Test error when video file doesn't exist."""
        episode = Episode(
            file_path=tmp_path / "nonexistent.mp4",
            show_name="Test Show",
            season=1,
            episode=1,
            duration_ms=None,
        )

        pipeline = AnalysisPipeline()
        with pytest.raises(AnalysisPipelineError, match="does not exist"):
            pipeline.analyze(episode)

    def test_analyze_with_mocked_pipeline(
        self, valid_episode: Episode, sample_analysis_result: AnalysisResult
    ) -> None:
        """Test analyze with fully mocked components."""
        # Mock all the components to avoid FFmpeg/Whisper/etc
        with patch("unrealitytv.analysis.pipeline.AnalysisPipeline._extract_audio"), \
             patch("unrealitytv.analysis.pipeline.AnalysisPipeline._transcribe_audio") as mock_transcribe, \
             patch("unrealitytv.analysis.pipeline.AnalysisPipeline._detect_segments") as mock_detect:

            mock_transcribe.return_value = []
            mock_detect.return_value = []

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert isinstance(result, AnalysisResult)
            assert result.episode == valid_episode
            assert len(result.segments) == 0


class TestAnalysisPipelineResourceManagement:
    """Tests for resource cleanup."""

    def test_close_releases_transcriber(self) -> None:
        """Test that close() releases transcriber."""
        pipeline = AnalysisPipeline()
        assert pipeline._transcriber is None
        pipeline.close()
        assert pipeline._transcriber is None

    def test_cleanup_temp_files_flag(self) -> None:
        """Test cleanup_temp_files flag."""
        pipeline = AnalysisPipeline(cleanup_temp_files=True)
        assert pipeline.cleanup_temp_files is True

        pipeline2 = AnalysisPipeline(cleanup_temp_files=False)
        assert pipeline2.cleanup_temp_files is False
