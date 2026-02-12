"""Segment applicator for applying skip segments to Plex."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from unrealitytv.models import AnalysisResult, SegmentApplicationResult, SkipSegment
from unrealitytv.plex.markers import MarkerType

if TYPE_CHECKING:
    from unrealitytv.config import Settings
    from unrealitytv.plex.client import PlexClient

logger = logging.getLogger(__name__)


class SegmentApplicatorError(Exception):
    """Exception raised when segment application fails."""

    pass


class SegmentApplicator:
    """Applies filtered skip segments to Plex markers."""

    def __init__(self, config: Settings, plex_client: Optional[PlexClient] = None):
        """Initialize the segment applicator.

        Args:
            config: Application settings
            plex_client: Optional Plex client for applying segments to Plex
        """
        self.config = config
        self.plex_client = plex_client
        logger.debug(
            f"Initialized SegmentApplicator with "
            f"enable_plex_application={config.enable_plex_application}"
        )

    def apply_segments(self, analysis_result: AnalysisResult) -> SegmentApplicationResult:
        """Apply filtered segments from analysis result.

        Filters segments based on confidence, duration, and type constraints,
        then applies them to Plex if enabled and client is available.

        Args:
            analysis_result: Analysis result containing segments to apply

        Returns:
            SegmentApplicationResult with application details and statistics
        """
        logger.info(
            f"Starting segment application for episode: {analysis_result.episode.show_name}"
        )

        # Filter segments
        filtered_segments, all_skip_reasons = self.filter_segments(
            analysis_result.segments, self.config
        )

        logger.info(
            f"Filtered {len(analysis_result.segments)} segments down to "
            f"{len(filtered_segments)} after applying constraints"
        )

        # Apply segments to Plex if enabled
        applied_count = 0
        application_errors = []
        plex_error = None

        if self.config.enable_plex_application and self.plex_client:
            for segment in filtered_segments:
                marker_type = self.segment_type_to_marker_type(segment.segment_type)
                if marker_type:
                    try:
                        # Attempt to apply marker to Plex
                        if analysis_result.episode.plex_metadata:
                            plex_item_id = analysis_result.episode.plex_metadata.plex_item_id
                            success = self.plex_client.apply_marker(
                                plex_item_id,
                                segment.start_ms,
                                segment.end_ms,
                                marker_type,
                            )
                            if success:
                                applied_count += 1
                                logger.debug(
                                    f"Applied {marker_type.value} marker for "
                                    f"{segment.segment_type} segment"
                                )
                            else:
                                error_msg = (
                                    f"Failed to apply {marker_type.value} marker "
                                    f"(no exception raised)"
                                )
                                application_errors.append(error_msg)
                                logger.warning(error_msg)
                        else:
                            error_msg = (
                                "Cannot apply segment: episode missing Plex metadata"
                            )
                            application_errors.append(error_msg)
                            logger.warning(error_msg)
                    except Exception as e:
                        error_msg = (
                            f"Error applying {marker_type.value} marker: {e}"
                        )
                        application_errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    logger.debug(
                        f"Skipping application of {segment.segment_type} "
                        f"(no Plex marker type)"
                    )

            if application_errors and not plex_error:
                plex_error = application_errors[0]

        logger.info(
            f"Segment application complete: "
            f"{applied_count} applied, "
            f"{len(all_skip_reasons)} skipped, "
            f"{len(application_errors)} errors"
        )

        return SegmentApplicationResult(
            episode=analysis_result.episode,
            segments_applied=applied_count,
            segments_skipped=len(all_skip_reasons),
            skip_reasons=all_skip_reasons,
            application_errors=application_errors,
            plex_error=plex_error,
        )

    def filter_segments(
        self, segments: list[SkipSegment], config: Settings
    ) -> tuple[list[SkipSegment], list[str]]:
        """Filter segments based on configured constraints.

        Filters by:
        - Confidence threshold
        - Minimum duration
        - Segment type exclusion list

        Args:
            segments: Segments to filter
            config: Configuration with filter constraints

        Returns:
            Tuple of (filtered_segments, skip_reasons_list)
        """
        filtered_segments = []
        skip_reasons = []

        for segment in segments:
            reason = None

            # Check confidence threshold
            if segment.confidence < config.confidence_threshold:
                reason = "confidence_too_low"
            # Check minimum duration
            elif (segment.end_ms - segment.start_ms) < config.min_segment_duration_ms:
                reason = "duration_too_short"
            # Check segment type exclusion
            elif segment.segment_type in config.skip_segment_types:
                reason = "type_filtered"

            if reason:
                skip_reasons.append(reason)
                logger.debug(
                    f"Filtering out {segment.segment_type} segment "
                    f"({reason}): {segment.start_ms}-{segment.end_ms}ms "
                    f"(confidence: {segment.confidence:.2f})"
                )
            else:
                filtered_segments.append(segment)
                logger.debug(
                    f"Keeping {segment.segment_type} segment: "
                    f"{segment.start_ms}-{segment.end_ms}ms "
                    f"(confidence: {segment.confidence:.2f})"
                )

        return filtered_segments, skip_reasons

    @staticmethod
    def segment_type_to_marker_type(segment_type: str) -> Optional[MarkerType]:
        """Convert segment type to Plex marker type.

        Maps segment detection types to applicable Plex marker types.
        Some segment types don't have direct Plex equivalents.

        Args:
            segment_type: Type of segment (recap, preview, etc.)

        Returns:
            Corresponding MarkerType enum or None if not applicable
        """
        type_map = {
            "recap": MarkerType.RECAP,
            "preview": MarkerType.PREVIEW,
        }
        return type_map.get(segment_type)
