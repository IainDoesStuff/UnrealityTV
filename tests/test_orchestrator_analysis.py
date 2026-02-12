"""Tests for analysis orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.config import Settings
from unrealitytv.models import (
    AnalysisResult,
    Episode,
    PlexMetadata,
    SegmentApplicationResult,
    SkipSegment,
)
from unrealitytv.orchestrator import AnalysisOrchestrator, AnalysisOrchestratorError


class TestAnalysisOrchestratorInit:
    """Test AnalysisOrchestrator initialization."""

    def test_init_with_config_only(self) -> None:
        """Test initialization with just config."""
        config = Settings()
        orchestrator = AnalysisOrchestrator(config)
        assert orchestrator.config == config
        assert orchestrator.plex_client is None
        assert orchestrator.analysis_pipeline is not None
        assert orchestrator.segment_applicator is not None

    def test_init_with_config_and_plex_client(self) -> None:
        """Test initialization with config and Plex client."""
        config = Settings()
        mock_plex_client = MagicMock()
        orchestrator = AnalysisOrchestrator(config, mock_plex_client)
        assert orchestrator.config == config
        assert orchestrator.plex_client == mock_plex_client

    def test_init_with_gpu_enabled(self) -> None:
        """Test initialization with GPU enabled in config."""
        config = Settings(gpu_enabled=True)
        orchestrator = AnalysisOrchestrator(config)
        assert orchestrator.config.gpu_enabled is True


class TestAnalyzeEpisode:
    """Test analyze_episode method."""

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_episode_success(self, mock_analyze) -> None:
        """Test successful episode analysis."""
        config = Settings()
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
        )

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]
        expected_result = AnalysisResult(episode=episode, segments=segments)
        mock_analyze.return_value = expected_result

        result = orchestrator.analyze_episode(episode)

        assert result == expected_result
        mock_analyze.assert_called_once_with(episode)

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_episode_pipeline_error(self, mock_analyze) -> None:
        """Test handling pipeline error during analysis."""
        config = Settings()
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/nonexistent/show.mkv"),
            show_name="Test Show",
        )

        from unrealitytv.analysis.pipeline import AnalysisPipelineError
        mock_analyze.side_effect = AnalysisPipelineError("Pipeline failed")

        with pytest.raises(AnalysisOrchestratorError) as exc_info:
            orchestrator.analyze_episode(episode)
        assert "Analysis failed" in str(exc_info.value)

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_analyze_episode_unexpected_error(self, mock_analyze) -> None:
        """Test handling unexpected error during analysis."""
        config = Settings()
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )

        mock_analyze.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(AnalysisOrchestratorError) as exc_info:
            orchestrator.analyze_episode(episode)
        assert "Unexpected error" in str(exc_info.value)


class TestApplySegments:
    """Test apply_segments method."""

    def test_apply_segments_success(self) -> None:
        """Test successful segment application."""
        config = Settings(enable_plex_application=False)
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )
        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]
        analysis_result = AnalysisResult(episode=episode, segments=segments)

        result = orchestrator.apply_segments(analysis_result)

        assert isinstance(result, SegmentApplicationResult)
        assert result.episode == episode

    def test_apply_segments_with_plex(self) -> None:
        """Test applying segments with Plex enabled."""
        config = Settings(enable_plex_application=True)
        mock_plex_client = MagicMock()
        mock_plex_client.apply_marker.return_value = True

        orchestrator = AnalysisOrchestrator(config, mock_plex_client)

        plex_metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="2",
        )
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            plex_metadata=plex_metadata,
        )
        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]
        analysis_result = AnalysisResult(episode=episode, segments=segments)

        result = orchestrator.apply_segments(analysis_result)

        assert result.segments_applied == 1


class TestProcessEpisode:
    """Test process_episode method (end-to-end)."""

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_process_episode_success(self, mock_analyze) -> None:
        """Test successful end-to-end processing."""
        config = Settings(enable_plex_application=False)
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
        )

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]
        analysis_result = AnalysisResult(episode=episode, segments=segments)
        mock_analyze.return_value = analysis_result

        result = orchestrator.process_episode(episode)

        assert isinstance(result, SegmentApplicationResult)
        assert result.episode == episode
        mock_analyze.assert_called_once_with(episode)

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_process_episode_analysis_failure(self, mock_analyze) -> None:
        """Test handling analysis failure during processing."""
        config = Settings()
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/nonexistent/show.mkv"),
            show_name="Test Show",
        )

        from unrealitytv.analysis.pipeline import AnalysisPipelineError
        mock_analyze.side_effect = AnalysisPipelineError("Analysis failed")

        with pytest.raises(AnalysisOrchestratorError):
            orchestrator.process_episode(episode)

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_process_episode_with_filtering(self, mock_analyze) -> None:
        """Test processing with segment filtering."""
        config = Settings(
            enable_plex_application=False,
            confidence_threshold=0.8,
        )
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.5,
                reason="test",
            ),
            SkipSegment(
                start_ms=6000,
                end_ms=10000,
                segment_type="recap",
                confidence=0.9,
                reason="test",
            ),
        ]
        analysis_result = AnalysisResult(episode=episode, segments=segments)
        mock_analyze.return_value = analysis_result

        result = orchestrator.process_episode(episode)

        assert result.segments_skipped > 0


class TestProcessEpisodesBatch:
    """Test process_episodes_batch method."""

    def test_batch_processing_disabled(self) -> None:
        """Test batch processing when disabled in config."""
        config = Settings(batch_processing=False)
        orchestrator = AnalysisOrchestrator(config)

        episodes = [
            Episode(
                file_path=Path("/video/show1.mkv"),
                show_name="Show 1",
            ),
        ]

        with pytest.raises(AnalysisOrchestratorError) as exc_info:
            orchestrator.process_episodes_batch(episodes)
        assert "Batch processing is disabled" in str(exc_info.value)

    @patch("unrealitytv.orchestrator.AnalysisOrchestrator.process_episode")
    def test_batch_processing_single_episode(self, mock_process) -> None:
        """Test batch processing with single episode."""
        config = Settings(batch_processing=True)
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )

        result = SegmentApplicationResult(
            episode=episode,
            segments_applied=1,
            segments_skipped=0,
        )
        mock_process.return_value = result

        episodes = [episode]
        results = orchestrator.process_episodes_batch(episodes)

        assert len(results) == 1
        assert results[0] == result
        mock_process.assert_called_once_with(episode)

    @patch("unrealitytv.orchestrator.AnalysisOrchestrator.process_episode")
    def test_batch_processing_multiple_episodes(self, mock_process) -> None:
        """Test batch processing with multiple episodes."""
        config = Settings(batch_processing=True)
        orchestrator = AnalysisOrchestrator(config)

        episodes = [
            Episode(
                file_path=Path(f"/video/show{i}.mkv"),
                show_name=f"Show {i}",
            )
            for i in range(3)
        ]

        results_list = [
            SegmentApplicationResult(
                episode=ep,
                segments_applied=i,
                segments_skipped=0,
            )
            for i, ep in enumerate(episodes)
        ]
        mock_process.side_effect = results_list

        results = orchestrator.process_episodes_batch(episodes)

        assert len(results) == 3
        assert mock_process.call_count == 3

    @patch("unrealitytv.orchestrator.AnalysisOrchestrator.process_episode")
    def test_batch_processing_with_failures(self, mock_process) -> None:
        """Test batch processing continues despite failures."""
        config = Settings(batch_processing=True)
        orchestrator = AnalysisOrchestrator(config)

        episodes = [
            Episode(
                file_path=Path(f"/video/show{i}.mkv"),
                show_name=f"Show {i}",
            )
            for i in range(3)
        ]

        result = SegmentApplicationResult(
            episode=episodes[0],
            segments_applied=1,
            segments_skipped=0,
        )

        # First call succeeds, second fails, third succeeds
        mock_process.side_effect = [
            result,
            AnalysisOrchestratorError("Processing failed"),
            result,
        ]

        results = orchestrator.process_episodes_batch(episodes)

        # Should return 2 successful results despite one failure
        assert len(results) == 2
        assert mock_process.call_count == 3

    @patch("unrealitytv.orchestrator.AnalysisOrchestrator.process_episode")
    def test_batch_processing_all_failures(self, mock_process) -> None:
        """Test batch processing when all episodes fail."""
        config = Settings(batch_processing=True)
        orchestrator = AnalysisOrchestrator(config)

        episodes = [
            Episode(
                file_path=Path(f"/video/show{i}.mkv"),
                show_name=f"Show {i}",
            )
            for i in range(2)
        ]

        mock_process.side_effect = AnalysisOrchestratorError("Processing failed")

        results = orchestrator.process_episodes_batch(episodes)

        # Should return empty list when all fail
        assert len(results) == 0
        assert mock_process.call_count == 2


class TestOrchestratorContextManager:
    """Test context manager support."""

    def test_context_manager_entry_exit(self) -> None:
        """Test using orchestrator as context manager."""
        config = Settings()
        with AnalysisOrchestrator(config) as orchestrator:
            assert orchestrator.config == config

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.close")
    def test_context_manager_cleanup(self, mock_close) -> None:
        """Test context manager calls close on exit."""
        config = Settings()
        with AnalysisOrchestrator(config):
            pass
        mock_close.assert_called_once()

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.close")
    def test_explicit_close(self, mock_close) -> None:
        """Test explicit close method."""
        config = Settings()
        orchestrator = AnalysisOrchestrator(config)
        orchestrator.close()
        mock_close.assert_called_once()


class TestOrchestratorIntegration:
    """Integration tests for orchestrator."""

    @patch("unrealitytv.analysis.pipeline.AnalysisPipeline.analyze")
    def test_full_pipeline_with_config(self, mock_analyze) -> None:
        """Test full pipeline with various config options."""
        config = Settings(
            gpu_enabled=False,
            confidence_threshold=0.75,
            min_segment_duration_ms=2000,
            detection_method="scene_detect",
            enable_plex_application=False,
            batch_processing=True,
            skip_segment_types=["filler"],
        )
        orchestrator = AnalysisOrchestrator(config)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
        )

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=4000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]
        analysis_result = AnalysisResult(episode=episode, segments=segments)
        mock_analyze.return_value = analysis_result

        result = orchestrator.process_episode(episode)

        assert result.episode == episode
        assert result.segments_applied == 0  # Plex disabled
