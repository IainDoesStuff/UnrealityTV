"""Analysis orchestrator coordinating the full pipeline."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

from unrealitytv.analysis.pipeline import AnalysisPipeline, AnalysisPipelineError
from unrealitytv.applicator import SegmentApplicator
from unrealitytv.models import AnalysisResult, Episode, SegmentApplicationResult

if TYPE_CHECKING:
    from unrealitytv.config import Settings
    from unrealitytv.plex.client import PlexClient

logger = logging.getLogger(__name__)


class AnalysisOrchestratorError(Exception):
    """Exception raised when orchestration fails."""

    pass


class AnalysisOrchestrator:
    """Orchestrates the complete analysis and application pipeline.

    Coordinates:
    1. Audio extraction from video
    2. Speech-to-text transcription
    3. Pattern matching for segment detection
    4. Segment filtering and application to Plex

    Attributes:
        config: Application configuration
        analysis_pipeline: Pipeline for episode analysis
        segment_applicator: Applicator for segment application
    """

    def __init__(
        self,
        config: Settings,
        plex_client: Optional[PlexClient] = None,
    ):
        """Initialize the analysis orchestrator.

        Args:
            config: Application settings
            plex_client: Optional Plex client for segment application

        Raises:
            AnalysisOrchestratorError: If initialization fails
        """
        self.config = config
        self.plex_client = plex_client
        self.analysis_pipeline = AnalysisPipeline(
            gpu_enabled=config.gpu_enabled,
        )
        self.segment_applicator = SegmentApplicator(config, plex_client)

        logger.debug(
            f"Initialized AnalysisOrchestrator with "
            f"detection_method={config.detection_method}, "
            f"batch_processing={config.batch_processing}"
        )

    def analyze_episode(self, episode: Episode) -> AnalysisResult:
        """Analyze an episode to detect skip segments.

        Runs the complete analysis pipeline:
        1. Audio extraction
        2. Transcription
        3. Pattern matching
        4. Segment detection

        Args:
            episode: Episode to analyze

        Returns:
            AnalysisResult with detected segments

        Raises:
            AnalysisOrchestratorError: If analysis fails
        """
        logger.info(f"Starting analysis for episode: {episode.show_name}")
        start_time = time.time()

        try:
            analysis_result = self.analysis_pipeline.analyze(episode)
            elapsed = time.time() - start_time

            logger.info(
                f"Analysis complete for {episode.show_name}: "
                f"found {len(analysis_result.segments)} segments in {elapsed:.2f}s"
            )
            return analysis_result

        except AnalysisPipelineError as e:
            msg = f"Analysis failed for {episode.show_name}: {e}"
            logger.error(msg)
            raise AnalysisOrchestratorError(msg) from e
        except Exception as e:
            msg = f"Unexpected error analyzing {episode.show_name}: {e}"
            logger.error(msg, exc_info=True)
            raise AnalysisOrchestratorError(msg) from e

    def apply_segments(
        self, analysis_result: AnalysisResult
    ) -> SegmentApplicationResult:
        """Apply detected segments to Plex.

        Filters segments and applies them to Plex if enabled.

        Args:
            analysis_result: Analysis result with segments to apply

        Returns:
            SegmentApplicationResult with application details

        Raises:
            AnalysisOrchestratorError: If application fails
        """
        logger.info(
            f"Starting segment application for {analysis_result.episode.show_name}"
        )

        try:
            application_result = self.segment_applicator.apply_segments(
                analysis_result
            )
            logger.info(
                f"Segment application complete: "
                f"{application_result.segments_applied} applied, "
                f"{application_result.segments_skipped} skipped"
            )
            return application_result

        except Exception as e:
            msg = (
                f"Error applying segments to "
                f"{analysis_result.episode.show_name}: {e}"
            )
            logger.error(msg)
            raise AnalysisOrchestratorError(msg) from e

    def process_episode(self, episode: Episode) -> SegmentApplicationResult:
        """Process an episode end-to-end.

        Runs analysis and applies segments to Plex in a single operation.

        Args:
            episode: Episode to process

        Returns:
            SegmentApplicationResult with full processing details

        Raises:
            AnalysisOrchestratorError: If processing fails
        """
        logger.info(f"Processing episode: {episode.show_name}")
        start_time = time.time()

        try:
            # Step 1: Analyze
            analysis_result = self.analyze_episode(episode)

            # Step 2: Apply
            application_result = self.apply_segments(analysis_result)

            elapsed = time.time() - start_time
            logger.info(
                f"Episode processing complete: {elapsed:.2f}s "
                f"({application_result.segments_applied} segments applied)"
            )

            return application_result

        except AnalysisOrchestratorError:
            raise
        except Exception as e:
            msg = f"Unexpected error processing {episode.show_name}: {e}"
            logger.error(msg, exc_info=True)
            raise AnalysisOrchestratorError(msg) from e

    def process_episodes_batch(
        self, episodes: list[Episode]
    ) -> list[SegmentApplicationResult]:
        """Process multiple episodes in batch.

        Processes episodes sequentially if batch processing is enabled.

        Args:
            episodes: List of episodes to process

        Returns:
            List of SegmentApplicationResult objects

        Raises:
            AnalysisOrchestratorError: If batch processing is disabled
        """
        if not self.config.batch_processing:
            msg = "Batch processing is disabled in configuration"
            logger.error(msg)
            raise AnalysisOrchestratorError(msg)

        logger.info(f"Starting batch processing of {len(episodes)} episodes")
        start_time = time.time()
        results = []
        failures = 0

        for i, episode in enumerate(episodes, 1):
            try:
                logger.info(f"Processing episode {i}/{len(episodes)}: {episode.show_name}")
                result = self.process_episode(episode)
                results.append(result)

            except AnalysisOrchestratorError as e:
                logger.warning(f"Failed to process episode {i}: {e}")
                failures += 1
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing episode {i}: {e}")
                failures += 1
                continue

        elapsed = time.time() - start_time
        logger.info(
            f"Batch processing complete: {len(results)} succeeded, "
            f"{failures} failed in {elapsed:.2f}s"
        )

        return results

    def close(self) -> None:
        """Clean up resources.

        Releases Whisper model and closes Plex client if open.
        """
        logger.debug("Closing orchestrator resources")
        try:
            self.analysis_pipeline.close()
        except Exception as e:
            logger.warning(f"Error closing pipeline: {e}")

        try:
            if self.plex_client:
                self.plex_client.close()
        except Exception as e:
            logger.warning(f"Error closing Plex client: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
