"""Tests for analysis pipeline that orchestrates the full processing workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.unrealitytv.analysis.pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
)
from src.unrealitytv.detection.patterns import PatternDetectionError
from src.unrealitytv.models import AnalysisResult, Episode, SkipSegment
from src.unrealitytv.transcription.whisper import (
    TranscriptSegment,
    WhisperError,
)


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
    """Create a sample transcript with mixed content."""
    return [
        TranscriptSegment(
            start_time_ms=0,
            end_time_ms=3000,
            text="Previously on the show...",
        ),
        TranscriptSegment(
            start_time_ms=3000,
            end_time_ms=6000,
            text="Now let's see what happens next.",
        ),
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


class TestAnalysisPipelineSuccessfulAnalysis:
    """Tests for successful pipeline execution."""

    def test_successful_full_pipeline_execution(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test successful execution of all pipeline stages."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            # Setup mocks
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            # Run pipeline
            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            # Verify result
            assert isinstance(result, AnalysisResult)
            assert result.episode == valid_episode
            assert len(result.segments) == 1
            assert result.segments[0].segment_type == "recap"

    def test_pipeline_with_empty_transcript(
        self, valid_episode: Episode
    ) -> None:
        """Test pipeline with no transcript segments."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = []
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = []
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert len(result.segments) == 0

    def test_pipeline_with_no_matching_segments(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment]
    ) -> None:
        """Test pipeline when transcript has no recap/preview keywords."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = []
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert len(result.segments) == 0

    def test_pipeline_with_multiple_skip_segments(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment]
    ) -> None:
        """Test pipeline detecting multiple recap/preview segments."""
        skip_segments = [
            SkipSegment(
                start_ms=0, end_ms=3000, segment_type="recap",
                confidence=0.9, reason="Detected: previously"
            ),
            SkipSegment(
                start_ms=150000, end_ms=180000, segment_type="preview",
                confidence=0.85, reason="Detected: coming up"
            ),
        ]

        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=180000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert len(result.segments) == 2


class TestAnalysisPipelineConfiguration:
    """Tests for pipeline configuration options."""

    def test_gpu_enabled_parameter(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that gpu_enabled parameter is passed to WhisperTranscriber."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline(gpu_enabled=True)
            pipeline.analyze(valid_episode)

            # Verify WhisperTranscriber was created with gpu_enabled=True
            mock_whisper_class.assert_called_once_with(gpu_enabled=True)

    def test_custom_recap_keywords(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that custom recap keywords are passed to KeywordMatcher."""
        custom_recap = ["flashback", "in the past"]

        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline(recap_keywords=custom_recap)
            pipeline.analyze(valid_episode)

            # Verify KeywordMatcher was created with custom keywords
            mock_matcher_class.assert_called_once()
            call_kwargs = mock_matcher_class.call_args[1]
            assert call_kwargs["recap_keywords"] == custom_recap

    def test_custom_preview_keywords(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that custom preview keywords are passed to KeywordMatcher."""
        custom_preview = ["teaser", "upcoming"]

        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline(preview_keywords=custom_preview)
            pipeline.analyze(valid_episode)

            # Verify KeywordMatcher was created with custom keywords
            call_kwargs = mock_matcher_class.call_args[1]
            assert call_kwargs["preview_keywords"] == custom_preview


class TestAnalysisPipelineErrorHandling:
    """Tests for error handling at each pipeline stage."""

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

    def test_audio_extraction_error(self, valid_episode: Episode) -> None:
        """Test error propagation from audio extraction."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio",
            side_effect=Exception("FFmpeg failed"),
        ), pytest.raises(AnalysisPipelineError, match="extraction"):
            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)

    def test_transcription_error(self, valid_episode: Episode) -> None:
        """Test error propagation from Whisper transcription."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, pytest.raises(
            AnalysisPipelineError, match="Transcription failed"
        ):
            mock_whisper = MagicMock()
            mock_whisper.transcribe.side_effect = WhisperError("Model failed")
            mock_whisper_class.return_value = mock_whisper

            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)

    def test_pattern_detection_error(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment]
    ) -> None:
        """Test error propagation from pattern matching."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class, pytest.raises(
            AnalysisPipelineError, match="Segment detection failed"
        ):
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.side_effect = PatternDetectionError(
                "Invalid pattern"
            )
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)

    def test_unexpected_error_handling(self, valid_episode: Episode) -> None:
        """Test handling of unexpected errors."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio",
            side_effect=RuntimeError("Unexpected error"),
        ), pytest.raises(
            AnalysisPipelineError, match="Unexpected error"
        ):
            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)


class TestAnalysisPipelineResourceManagement:
    """Tests for resource allocation and cleanup."""

    def test_episode_duration_detection(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that episode duration is populated from file."""
        detected_duration = 75000

        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=detected_duration,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            assert valid_episode.duration_ms is None
            pipeline.analyze(valid_episode)
            assert valid_episode.duration_ms == detected_duration

    def test_close_releases_transcriber(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that close() releases the WhisperTranscriber."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)

            assert pipeline._transcriber is not None
            pipeline.close()
            assert pipeline._transcriber is None

    def test_cleanup_on_error(self, valid_episode: Episode) -> None:
        """Test that resources are cleaned up even on error."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio",
            side_effect=Exception("Error"),
        ), pytest.raises(AnalysisPipelineError):
            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)

        # Transcriber should be None after cleanup
        assert pipeline._transcriber is None

    def test_cleanup_temp_files_flag_true(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test temporary file cleanup when flag is True."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline(cleanup_temp_files=True)
            result = pipeline.analyze(valid_episode)

            assert isinstance(result, AnalysisResult)

    def test_cleanup_temp_files_flag_false(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that temporary files are kept when flag is False."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline(cleanup_temp_files=False)
            result = pipeline.analyze(valid_episode)

            assert isinstance(result, AnalysisResult)


class TestAnalysisPipelineLazyLoading:
    """Tests for lazy loading and reuse of pipeline components."""

    def test_transcriber_lazy_loading(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that WhisperTranscriber is lazily loaded on first analyze."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            assert pipeline._transcriber is None
            pipeline.analyze(valid_episode)
            assert pipeline._transcriber is not None

    def test_matcher_lazy_loading(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that KeywordMatcher is lazily loaded on first analyze."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            assert pipeline._matcher is None
            pipeline.analyze(valid_episode)
            assert pipeline._matcher is not None

    def test_transcriber_reuse_across_calls(
        self, valid_episode: Episode, tmp_path: Path,
        sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that WhisperTranscriber is reused across multiple analyze calls."""
        episode2 = Episode(
            file_path=tmp_path / "episode2.mp4",
            show_name="Test Show",
            season=1,
            episode=2,
            duration_ms=None,
        )
        episode2.file_path.write_bytes(b"fake video")

        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            pipeline.analyze(valid_episode)
            first_transcriber = pipeline._transcriber

            pipeline.analyze(episode2)
            second_transcriber = pipeline._transcriber

            # Should be the same instance
            assert first_transcriber is second_transcriber
            # Should only be created once
            mock_whisper_class.assert_called_once()


class TestAnalysisPipelineResultMetadata:
    """Tests for result metadata and accuracy."""

    def test_result_contains_episode(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that result contains the input episode."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert result.episode is valid_episode

    def test_result_contains_detected_segments(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that result contains all detected segments."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert len(result.segments) == len(sample_skip_segments)
            assert result.segments == sample_skip_segments

    def test_result_type_is_analysis_result(
        self, valid_episode: Episode, sample_transcript: list[TranscriptSegment],
        sample_skip_segments: list[SkipSegment]
    ) -> None:
        """Test that result is an AnalysisResult instance."""
        with patch(
            "src.unrealitytv.analysis.pipeline.extract_audio"
        ), patch(
            "src.unrealitytv.analysis.pipeline.get_duration_ms",
            return_value=60000,
        ), patch(
            "src.unrealitytv.analysis.pipeline.WhisperTranscriber"
        ) as mock_whisper_class, patch(
            "src.unrealitytv.analysis.pipeline.KeywordMatcher"
        ) as mock_matcher_class:
            mock_whisper = MagicMock()
            mock_whisper.transcribe.return_value = sample_transcript
            mock_whisper_class.return_value = mock_whisper

            mock_matcher = MagicMock()
            mock_matcher.detect_segments.return_value = sample_skip_segments
            mock_matcher_class.return_value = mock_matcher

            pipeline = AnalysisPipeline()
            result = pipeline.analyze(valid_episode)

            assert isinstance(result, AnalysisResult)
