"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from unrealitytv.analysis import AnalysisPipelineError
from unrealitytv.cli import analyze
from unrealitytv.models import AnalysisResult, Episode, SkipSegment


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_episode(tmp_path: Path) -> Episode:
    """Create a sample episode with valid file."""
    video_file = tmp_path / "TestShow.S01E05.mkv"
    video_file.write_bytes(b"fake video content")
    return Episode(
        file_path=video_file,
        show_name="Test Show",
        season=1,
        episode=5,
        duration_ms=300000,  # 5 minutes
    )


@pytest.fixture
def sample_analysis_result(sample_episode: Episode) -> AnalysisResult:
    """Create a sample analysis result with segments."""
    return AnalysisResult(
        episode=sample_episode,
        segments=[
            SkipSegment(
                start_ms=0,
                end_ms=15000,
                segment_type="recap",
                confidence=0.95,
                reason="Detected: previously, last episode",
            ),
            SkipSegment(
                start_ms=285000,
                end_ms=300000,
                segment_type="preview",
                confidence=0.85,
                reason="Detected: coming up, next episode",
            ),
        ],
    )


class TestAnalyzeCommand:
    """Tests for the analyze CLI command."""

    def test_analyze_success_with_segments(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult, tmp_path: Path
    ) -> None:
        """Test successful analysis with segments found."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            assert "Test Show" in result.output
            assert "Detected 2 skip segment(s)" in result.output
            assert "recap" in result.output.lower()
            assert "preview" in result.output.lower()
            mock_pipeline.close.assert_called_once()

    def test_analyze_success_no_segments(
        self, cli_runner: CliRunner, sample_episode: Episode, tmp_path: Path
    ) -> None:
        """Test successful analysis with no segments found."""
        result_no_segments = AnalysisResult(episode=sample_episode, segments=[])

        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = result_no_segments
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            assert "Detected 0 skip segment(s)" in result.output
            assert "No segments detected" in result.output

    def test_analyze_with_output_json(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult, tmp_path: Path
    ) -> None:
        """Test saving analysis results to JSON file."""
        output_file = tmp_path / "analysis.json"

        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(
                analyze, [str(sample_episode.file_path), "--output",
                         str(output_file)]
            )

            assert result.exit_code == 0
            assert "Analysis results saved to" in result.output

    def test_analyze_file_not_found(self, cli_runner: CliRunner) -> None:
        """Test error when video file doesn't exist."""
        # Click validates file exists before calling the command,
        # so we check that Click returns an error
        result = cli_runner.invoke(analyze, ["/nonexistent/video.mp4"])

        assert result.exit_code != 0
        assert "does not exist" in result.output or "No such file" in result.output

    def test_analyze_pipeline_error(
        self, cli_runner: CliRunner, sample_episode: Episode
    ) -> None:
        """Test error when analysis pipeline fails."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.side_effect = AnalysisPipelineError("Pipeline error")
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code != 0
            assert "Analysis failed" in result.output or "Pipeline error" in result.output

    def test_analyze_gpu_flag(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult
    ) -> None:
        """Test GPU flag is passed to pipeline."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(
                analyze, [str(sample_episode.file_path), "--gpu"]
            )

            assert result.exit_code == 0
            mock_pipeline_class.assert_called_once_with(gpu_enabled=True)

    def test_analyze_no_gpu_flag(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult
    ) -> None:
        """Test GPU is disabled by default."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            mock_pipeline_class.assert_called_once_with(gpu_enabled=False)

    def test_analyze_episode_parsing(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult
    ) -> None:
        """Test that episode is parsed from filename."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ) as mock_parse, patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            mock_parse.assert_called_once()
            # Verify the parsed episode was used
            call_args = mock_pipeline.analyze.call_args
            assert call_args[0][0].show_name == "Test Show"

    def test_analyze_displays_episode_info(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult
    ) -> None:
        """Test that episode information is displayed."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            assert "Episode Information:" in result.output
            assert "Show: Test Show" in result.output
            assert "Season: 1" in result.output
            assert "Episode: 5" in result.output

    def test_analyze_displays_segment_details(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult
    ) -> None:
        """Test that segment details are displayed correctly."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            # Check that segment information is displayed
            assert "RECAP" in result.output or "recap" in result.output
            assert "PREVIEW" in result.output or "preview" in result.output
            # Check confidence percentage is shown
            assert "95%" in result.output or "85%" in result.output

    def test_analyze_handles_exception_during_pipeline(
        self, cli_runner: CliRunner, sample_episode: Episode
    ) -> None:
        """Test that unexpected exceptions are caught and displayed."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.side_effect = RuntimeError("Unexpected error")
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code != 0
            assert "Unexpected error" in result.output

    def test_analyze_closes_pipeline_on_success(
        self, cli_runner: CliRunner, sample_episode: Episode,
        sample_analysis_result: AnalysisResult
    ) -> None:
        """Test that pipeline is closed after successful analysis."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = sample_analysis_result
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code == 0
            mock_pipeline.close.assert_called_once()

    def test_analyze_closes_pipeline_on_error(
        self, cli_runner: CliRunner, sample_episode: Episode
    ) -> None:
        """Test that pipeline is closed even on error."""
        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=sample_episode,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.side_effect = AnalysisPipelineError("Error")
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(sample_episode.file_path)])

            assert result.exit_code != 0
            mock_pipeline.close.assert_called_once()

    def test_analyze_handles_missing_optional_episode_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test analysis with episode that has no season/episode info."""
        # Create actual file first since Click validates it exists
        video_file = tmp_path / "Unknown.mkv"
        video_file.write_bytes(b"fake video")

        episode_no_metadata = Episode(
            file_path=video_file,
            show_name="Unknown Show",
            season=None,
            episode=None,
            duration_ms=None,
        )

        result_no_metadata = AnalysisResult(
            episode=episode_no_metadata, segments=[]
        )

        with patch(
            "unrealitytv.cli.parse_episode",
            return_value=episode_no_metadata,
        ), patch(
            "unrealitytv.cli.AnalysisPipeline"
        ) as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze.return_value = result_no_metadata
            mock_pipeline_class.return_value = mock_pipeline

            result = cli_runner.invoke(analyze, [str(video_file)])

            assert result.exit_code == 0
            assert "Unknown Show" in result.output
