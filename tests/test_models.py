"""Tests for data models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from unrealitytv.models import (
    AnalysisResult,
    Episode,
    PlexMetadata,
    SceneBoundary,
    SkipSegment,
)


class TestEpisode:
    """Test Episode model."""

    def test_episode_with_all_fields(self):
        """Test Episode instantiation with all fields."""
        ep = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
            duration_ms=3600000,
        )
        assert ep.file_path == Path("/video/show.mkv")
        assert ep.show_name == "Test Show"
        assert ep.season == 1
        assert ep.episode == 5
        assert ep.duration_ms == 3600000

    def test_episode_with_optional_fields_none(self):
        """Test Episode with optional fields as None."""
        ep = Episode(
            file_path=Path("/video/unknown.mkv"),
            show_name="Unknown Show",
        )
        assert ep.season is None
        assert ep.episode is None
        assert ep.duration_ms is None


class TestSkipSegment:
    """Test SkipSegment model."""

    def test_valid_skip_segment(self):
        """Test valid SkipSegment creation."""
        seg = SkipSegment(
            start_ms=1000,
            end_ms=5000,
            segment_type="recap",
            confidence=0.95,
            reason="Previously on...",
        )
        assert seg.start_ms == 1000
        assert seg.end_ms == 5000
        assert seg.confidence == 0.95

    def test_confidence_validation_bounds(self):
        """Test confidence bounds validation."""
        # Confidence too high
        with pytest.raises(ValidationError):
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=1.5,
                reason="Invalid",
            )

        # Confidence too low
        with pytest.raises(ValidationError):
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="recap",
                confidence=-0.1,
                reason="Invalid",
            )

    def test_end_before_start_validation(self):
        """Test that end_ms must be greater than start_ms."""
        with pytest.raises(ValidationError):
            SkipSegment(
                start_ms=5000,
                end_ms=1000,
                segment_type="recap",
                confidence=0.5,
                reason="Invalid",
            )

        # Equal start and end should also fail
        with pytest.raises(ValidationError):
            SkipSegment(
                start_ms=1000,
                end_ms=1000,
                segment_type="recap",
                confidence=0.5,
                reason="Invalid",
            )

    def test_segment_type_validation(self):
        """Test that segment_type must be valid literal."""
        with pytest.raises(ValidationError):
            SkipSegment(
                start_ms=1000,
                end_ms=5000,
                segment_type="invalid_type",
                confidence=0.5,
                reason="Invalid",
            )


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_analysis_result_creation(self):
        """Test AnalysisResult with episode and segments."""
        ep = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
        )
        seg1 = SkipSegment(
            start_ms=1000,
            end_ms=5000,
            segment_type="recap",
            confidence=0.9,
            reason="Previously on...",
        )
        seg2 = SkipSegment(
            start_ms=42000,
            end_ms=46000,
            segment_type="preview",
            confidence=0.85,
            reason="Coming up...",
        )

        result = AnalysisResult(episode=ep, segments=[seg1, seg2])
        assert result.episode == ep
        assert len(result.segments) == 2
        assert result.segments[0].segment_type == "recap"

    def test_to_json_and_from_json_roundtrip(self):
        """Test JSON serialization round-trip."""
        ep = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
        )
        seg = SkipSegment(
            start_ms=1000,
            end_ms=5000,
            segment_type="recap",
            confidence=0.9,
            reason="Previously on...",
        )
        result = AnalysisResult(episode=ep, segments=[seg])

        # Serialize to JSON
        json_str = result.to_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        result2 = AnalysisResult.from_json(json_str)
        assert result2.episode.show_name == ep.show_name
        assert result2.episode.season == ep.season
        assert len(result2.segments) == 1
        assert result2.segments[0].confidence == 0.9


class TestSceneBoundary:
    """Test SceneBoundary model."""

    def test_scene_boundary_creation(self):
        """Test SceneBoundary instantiation."""
        boundary = SceneBoundary(
            start_ms=1000,
            end_ms=5000,
            scene_index=0,
        )
        assert boundary.start_ms == 1000
        assert boundary.end_ms == 5000
        assert boundary.scene_index == 0


class TestPlexMetadata:
    """Test PlexMetadata model."""

    def test_plex_metadata_creation(self):
        """Test PlexMetadata instantiation."""
        metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="section_1",
        )
        assert metadata.plex_item_id == "12345"
        assert metadata.plex_library_key == "1"
        assert metadata.plex_section_key == "section_1"

    def test_plex_metadata_serialization(self):
        """Test PlexMetadata serialization."""
        metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="section_1",
        )
        data = metadata.model_dump()
        assert data["plex_item_id"] == "12345"
        assert data["plex_library_key"] == "1"


class TestEpisodeWithPlexMetadata:
    """Test Episode model with plex_metadata field."""

    def test_episode_with_plex_metadata(self):
        """Test Episode with plex_metadata field."""
        metadata = PlexMetadata(
            plex_item_id="12345",
            plex_library_key="1",
            plex_section_key="section_1",
        )
        ep = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
            duration_ms=3600000,
            plex_metadata=metadata,
        )
        assert ep.plex_metadata is not None
        assert ep.plex_metadata.plex_item_id == "12345"

    def test_episode_without_plex_metadata(self):
        """Test Episode without plex_metadata (backward compatibility)."""
        ep = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            season=1,
            episode=5,
        )
        assert ep.plex_metadata is None

    def test_episode_with_none_plex_metadata(self):
        """Test Episode with explicit None plex_metadata."""
        ep = Episode(
            file_path=Path("/video/show.mkv"),
            show_name="Test Show",
            plex_metadata=None,
        )
        assert ep.plex_metadata is None
