"""Tests for segment applicator."""

from pathlib import Path
from unittest.mock import MagicMock

from unrealitytv.applicator import SegmentApplicator
from unrealitytv.config import Settings
from unrealitytv.models import (
    AnalysisResult,
    Episode,
    PlexMetadata,
    SegmentApplicationResult,
    SkipSegment,
)
from unrealitytv.plex.markers import MarkerType


class TestSegmentApplicatorInit:
    """Test SegmentApplicator initialization."""

    def test_init_with_config_only(self) -> None:
        """Test initialization with just config."""
        config = Settings()
        applicator = SegmentApplicator(config)
        assert applicator.config == config
        assert applicator.plex_client is None

    def test_init_with_config_and_plex_client(self) -> None:
        """Test initialization with config and Plex client."""
        config = Settings()
        mock_plex_client = MagicMock()
        applicator = SegmentApplicator(config, mock_plex_client)
        assert applicator.config == config
        assert applicator.plex_client == mock_plex_client


class TestSegmentTypeToMarkerType:
    """Test segment type to marker type conversion."""

    def test_recap_to_marker_type(self) -> None:
        """Test converting recap segment to marker type."""
        marker_type = SegmentApplicator.segment_type_to_marker_type("recap")
        assert marker_type == MarkerType.RECAP

    def test_preview_to_marker_type(self) -> None:
        """Test converting preview segment to marker type."""
        marker_type = SegmentApplicator.segment_type_to_marker_type("preview")
        assert marker_type == MarkerType.PREVIEW

    def test_unmapped_segment_type(self) -> None:
        """Test converting unmapped segment type returns None."""
        marker_type = SegmentApplicator.segment_type_to_marker_type(
            "repeated_establishing_shot"
        )
        assert marker_type is None

    def test_filler_segment_type(self) -> None:
        """Test converting filler segment returns None."""
        marker_type = SegmentApplicator.segment_type_to_marker_type("filler")
        assert marker_type is None

    def test_flashback_segment_type(self) -> None:
        """Test converting flashback segment returns None."""
        marker_type = SegmentApplicator.segment_type_to_marker_type("flashback")
        assert marker_type is None

    def test_unknown_segment_type(self) -> None:
        """Test converting unknown segment type returns None."""
        marker_type = SegmentApplicator.segment_type_to_marker_type("unknown_type")
        assert marker_type is None


class TestFilterSegments:
    """Test segment filtering."""

    def test_no_filtering_needed(self) -> None:
        """Test when no segments need filtering."""
        config = Settings(
            confidence_threshold=0.5,
            min_segment_duration_ms=1000,
            skip_segment_types=[],
        )
        applicator = SegmentApplicator(config)

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]

        filtered, reasons = applicator.filter_segments(segments, config)
        assert len(filtered) == 1
        assert len(reasons) == 0

    def test_filter_by_confidence_threshold(self) -> None:
        """Test filtering by confidence threshold."""
        config = Settings(confidence_threshold=0.8)
        applicator = SegmentApplicator(config)

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

        filtered, reasons = applicator.filter_segments(segments, config)
        assert len(filtered) == 1
        assert filtered[0].confidence == 0.9
        assert "confidence_too_low" in reasons

    def test_filter_by_minimum_duration(self) -> None:
        """Test filtering by minimum duration."""
        config = Settings(min_segment_duration_ms=3000)
        applicator = SegmentApplicator(config)

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=2000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
            SkipSegment(
                start_ms=3000,
                end_ms=7000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
        ]

        filtered, reasons = applicator.filter_segments(segments, config)
        assert len(filtered) == 1
        assert filtered[0].start_ms == 3000
        assert "duration_too_short" in reasons

    def test_filter_by_segment_type(self) -> None:
        """Test filtering by segment type exclusion."""
        config = Settings(skip_segment_types=["recap"])
        applicator = SegmentApplicator(config)

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
            SkipSegment(
                start_ms=6000,
                end_ms=10000,
                segment_type="preview",
                confidence=0.8,
                reason="test",
            ),
        ]

        filtered, reasons = applicator.filter_segments(segments, config)
        assert len(filtered) == 1
        assert filtered[0].segment_type == "preview"
        assert "type_filtered" in reasons

    def test_filter_all_segments(self) -> None:
        """Test when all segments are filtered."""
        config = Settings(
            confidence_threshold=0.9,
            min_segment_duration_ms=10000,
            skip_segment_types=["recap", "preview"],
        )
        applicator = SegmentApplicator(config)

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.5,
                reason="test",
            ),
        ]

        filtered, reasons = applicator.filter_segments(segments, config)
        assert len(filtered) == 0
        assert len(reasons) > 0

    def test_multiple_segments_mixed_filtering(self) -> None:
        """Test filtering with mixed results."""
        config = Settings(
            confidence_threshold=0.7,
            min_segment_duration_ms=2000,
            skip_segment_types=["filler"],
        )
        applicator = SegmentApplicator(config)

        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
            SkipSegment(
                start_ms=6000,
                end_ms=7000,
                segment_type="recap",
                confidence=0.8,
                reason="test",
            ),
            SkipSegment(
                start_ms=8000,
                end_ms=12000,
                segment_type="filler",
                confidence=0.8,
                reason="test",
            ),
            SkipSegment(
                start_ms=13000,
                end_ms=17000,
                segment_type="preview",
                confidence=0.6,
                reason="test",
            ),
        ]

        filtered, reasons = applicator.filter_segments(segments, config)
        assert len(filtered) == 1
        assert filtered[0].segment_type == "recap"
        assert filtered[0].start_ms == 1000


class TestApplySegments:
    """Test segment application."""

    def test_apply_segments_plex_disabled(self) -> None:
        """Test applying segments with Plex disabled."""
        config = Settings(enable_plex_application=False)
        applicator = SegmentApplicator(config)

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

        result = applicator.apply_segments(analysis_result)

        assert isinstance(result, SegmentApplicationResult)
        assert result.segments_applied == 0
        assert result.plex_error is None

    def test_apply_segments_with_plex_client(self) -> None:
        """Test applying segments with Plex client."""
        config = Settings(enable_plex_application=True)
        mock_plex_client = MagicMock()
        mock_plex_client.apply_marker.return_value = True

        applicator = SegmentApplicator(config, mock_plex_client)

        plex_metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="2",
        )
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
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

        result = applicator.apply_segments(analysis_result)

        assert result.segments_applied == 1
        assert result.segments_skipped == 0
        assert result.plex_error is None
        mock_plex_client.apply_marker.assert_called_once()

    def test_apply_segments_plex_error(self) -> None:
        """Test handling Plex API errors."""
        config = Settings(enable_plex_application=True)
        mock_plex_client = MagicMock()
        mock_plex_client.apply_marker.side_effect = Exception("Plex API error")

        applicator = SegmentApplicator(config, mock_plex_client)

        plex_metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="2",
        )
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
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

        result = applicator.apply_segments(analysis_result)

        assert result.segments_applied == 0
        assert len(result.application_errors) > 0
        assert result.plex_error is not None

    def test_apply_segments_missing_plex_metadata(self) -> None:
        """Test applying segments when episode missing Plex metadata."""
        config = Settings(enable_plex_application=True)
        mock_plex_client = MagicMock()

        applicator = SegmentApplicator(config, mock_plex_client)

        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
            plex_metadata=None,
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

        result = applicator.apply_segments(analysis_result)

        assert result.segments_applied == 0
        assert len(result.application_errors) > 0
        mock_plex_client.apply_marker.assert_not_called()

    def test_apply_segments_unmappable_type(self) -> None:
        """Test applying segments with unmappable type."""
        config = Settings(enable_plex_application=True)
        mock_plex_client = MagicMock()

        applicator = SegmentApplicator(config, mock_plex_client)

        plex_metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="2",
        )
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
            plex_metadata=plex_metadata,
        )
        segments = [
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="filler",
                confidence=0.8,
                reason="test",
            ),
        ]
        analysis_result = AnalysisResult(episode=episode, segments=segments)

        result = applicator.apply_segments(analysis_result)

        assert result.segments_applied == 0
        mock_plex_client.apply_marker.assert_not_called()

    def test_apply_segments_filtered_out(self) -> None:
        """Test applying segments when some are filtered."""
        config = Settings(
            enable_plex_application=True,
            confidence_threshold=0.8,
        )
        mock_plex_client = MagicMock()
        mock_plex_client.apply_marker.return_value = True

        applicator = SegmentApplicator(config, mock_plex_client)

        plex_metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="2",
        )
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
            plex_metadata=plex_metadata,
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

        result = applicator.apply_segments(analysis_result)

        assert result.segments_applied == 1
        assert result.segments_skipped == 1


class TestApplicationResultModel:
    """Test SegmentApplicationResult model."""

    def test_create_application_result(self) -> None:
        """Test creating application result."""
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )
        result = SegmentApplicationResult(
            episode=episode,
            segments_applied=5,
            segments_skipped=2,
            skip_reasons=["confidence_too_low"],
            application_errors=[],
        )

        assert result.episode == episode
        assert result.segments_applied == 5
        assert result.segments_skipped == 2
        assert result.plex_error is None

    def test_application_result_serialization(self) -> None:
        """Test serializing application result."""
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )
        result = SegmentApplicationResult(
            episode=episode,
            segments_applied=5,
            segments_skipped=2,
            skip_reasons=["confidence_too_low"],
            application_errors=[],
        )

        json_str = result.to_json()
        assert isinstance(json_str, str)
        assert "segments_applied" in json_str

    def test_application_result_deserialization(self) -> None:
        """Test deserializing application result."""
        episode = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
        )
        result = SegmentApplicationResult(
            episode=episode,
            segments_applied=5,
            segments_skipped=2,
            skip_reasons=["confidence_too_low"],
            application_errors=[],
        )

        json_str = result.to_json()
        deserialized = SegmentApplicationResult.from_json(json_str)

        assert deserialized.segments_applied == result.segments_applied
        assert deserialized.segments_skipped == result.segments_skipped
