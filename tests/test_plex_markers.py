"""Tests for Plex marker management."""

from __future__ import annotations

from datetime import datetime

import pytest

from unrealitytv.plex.markers import MarkerType, PlexMarker


class TestMarkerType:
    """Tests for MarkerType enum."""

    def test_marker_type_intro(self) -> None:
        """Test INTRO marker type."""
        assert MarkerType.INTRO.value == "intro"

    def test_marker_type_credits(self) -> None:
        """Test CREDITS marker type."""
        assert MarkerType.CREDITS.value == "credits"

    def test_marker_type_commercial(self) -> None:
        """Test COMMERCIAL marker type."""
        assert MarkerType.COMMERCIAL.value == "commercial"

    def test_marker_type_preview(self) -> None:
        """Test PREVIEW marker type."""
        assert MarkerType.PREVIEW.value == "preview"

    def test_marker_type_recap(self) -> None:
        """Test RECAP marker type."""
        assert MarkerType.RECAP.value == "recap"


class TestPlexMarker:
    """Tests for PlexMarker model."""

    def test_marker_creation(self) -> None:
        """Test creating a PlexMarker."""
        marker = PlexMarker(
            item_id="12345",
            start_ms=1000,
            end_ms=5000,
            marker_type=MarkerType.INTRO,
        )

        assert marker.item_id == "12345"
        assert marker.start_ms == 1000
        assert marker.end_ms == 5000
        assert marker.marker_type == MarkerType.INTRO

    def test_marker_with_timestamp(self) -> None:
        """Test creating a PlexMarker with timestamp."""
        now = datetime.now()
        marker = PlexMarker(
            item_id="12345",
            start_ms=1000,
            end_ms=5000,
            marker_type=MarkerType.INTRO,
            created_at=now,
        )

        assert marker.created_at == now

    def test_marker_validation_end_after_start(self) -> None:
        """Test that end_ms must be greater than start_ms."""
        with pytest.raises(ValueError, match="end_ms must be greater"):
            PlexMarker(
                item_id="12345",
                start_ms=5000,
                end_ms=1000,
                marker_type=MarkerType.INTRO,
            )

    def test_marker_validation_negative_start(self) -> None:
        """Test that start_ms cannot be negative."""
        with pytest.raises(ValueError):
            PlexMarker(
                item_id="12345",
                start_ms=-1000,
                end_ms=5000,
                marker_type=MarkerType.INTRO,
            )

    def test_marker_to_dict(self) -> None:
        """Test converting marker to dictionary."""
        marker = PlexMarker(
            item_id="12345",
            start_ms=1000,
            end_ms=5000,
            marker_type=MarkerType.INTRO,
        )

        marker_dict = marker.to_dict()

        assert marker_dict["item_id"] == "12345"
        assert marker_dict["start_ms"] == 1000
        assert marker_dict["end_ms"] == 5000
        assert marker_dict["marker_type"] == "intro"

    def test_marker_serialization(self) -> None:
        """Test JSON serialization of marker."""
        marker = PlexMarker(
            item_id="12345",
            start_ms=1000,
            end_ms=5000,
            marker_type=MarkerType.INTRO,
        )

        json_str = marker.model_dump_json()
        assert "item_id" in json_str
        assert "12345" in json_str
        assert "intro" in json_str
