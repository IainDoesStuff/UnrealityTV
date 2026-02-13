"""Tests for Phase 8 visual duplicate detection config."""

from __future__ import annotations

import pytest

from unrealitytv.config import Settings


class TestVisualDuplicateConfigFields:
    """Tests for visual duplicate configuration fields."""

    def test_visual_duplicate_fields_exist(self):
        """Test that all visual duplicate fields exist and have defaults."""
        settings = Settings()

        assert hasattr(settings, "visual_duplicate_detection_enabled")
        assert hasattr(settings, "visual_duplicate_fps")
        assert hasattr(settings, "visual_duplicate_hamming_threshold")
        assert hasattr(settings, "visual_duplicate_min_duration_ms")
        assert hasattr(settings, "visual_duplicate_gap_tolerance_ms")

    def test_default_values(self):
        """Test default values for visual duplicate fields."""
        settings = Settings()

        assert settings.visual_duplicate_detection_enabled is False
        assert settings.visual_duplicate_fps == 1.0
        assert settings.visual_duplicate_hamming_threshold == 8
        assert settings.visual_duplicate_min_duration_ms == 3000
        assert settings.visual_duplicate_gap_tolerance_ms == 2000

    def test_fps_bounds_validation(self):
        """Test that fps is validated within 0.1-10.0 range."""
        # Too low
        with pytest.raises(ValueError):
            Settings(visual_duplicate_fps=0.05)

        # Too high
        with pytest.raises(ValueError):
            Settings(visual_duplicate_fps=15.0)

        # Valid values
        assert Settings(visual_duplicate_fps=0.1).visual_duplicate_fps == 0.1
        assert Settings(visual_duplicate_fps=5.0).visual_duplicate_fps == 5.0
        assert Settings(visual_duplicate_fps=10.0).visual_duplicate_fps == 10.0

    def test_hamming_threshold_bounds_validation(self):
        """Test that hamming_threshold is validated within 0-64 range."""
        # Too high
        with pytest.raises(ValueError):
            Settings(visual_duplicate_hamming_threshold=65)

        # Valid values
        assert Settings(visual_duplicate_hamming_threshold=0).visual_duplicate_hamming_threshold == 0
        assert Settings(visual_duplicate_hamming_threshold=32).visual_duplicate_hamming_threshold == 32
        assert Settings(visual_duplicate_hamming_threshold=64).visual_duplicate_hamming_threshold == 64

    def test_duration_bounds_validation(self):
        """Test that duration fields accept non-negative values."""
        # Negative should fail
        with pytest.raises(ValueError):
            Settings(visual_duplicate_min_duration_ms=-1)

        with pytest.raises(ValueError):
            Settings(visual_duplicate_gap_tolerance_ms=-1)

        # Zero and positive should work
        assert Settings(visual_duplicate_min_duration_ms=0).visual_duplicate_min_duration_ms == 0
        assert Settings(visual_duplicate_gap_tolerance_ms=0).visual_duplicate_gap_tolerance_ms == 0

    def test_detection_method_includes_visual_duplicates(self):
        """Test that detection_method validator accepts visual_duplicates."""
        settings = Settings(detection_method="visual_duplicates")
        assert settings.detection_method == "visual_duplicates"

    def test_detection_method_invalid_value(self):
        """Test that invalid detection_method raises error."""
        with pytest.raises(ValueError) as exc_info:
            Settings(detection_method="invalid_method")

        assert "visual_duplicates" in str(exc_info.value)

    def test_enable_visual_duplicates(self):
        """Test enabling visual duplicate detection."""
        settings = Settings(
            visual_duplicate_detection_enabled=True,
            visual_duplicate_fps=2.0,
            detection_method="visual_duplicates",
        )

        assert settings.visual_duplicate_detection_enabled is True
        assert settings.visual_duplicate_fps == 2.0
        assert settings.detection_method == "visual_duplicates"

    def test_all_fields_together(self):
        """Test creating settings with all visual duplicate fields."""
        settings = Settings(
            visual_duplicate_detection_enabled=True,
            visual_duplicate_fps=1.5,
            visual_duplicate_hamming_threshold=10,
            visual_duplicate_min_duration_ms=2000,
            visual_duplicate_gap_tolerance_ms=1500,
        )

        assert settings.visual_duplicate_detection_enabled is True
        assert settings.visual_duplicate_fps == 1.5
        assert settings.visual_duplicate_hamming_threshold == 10
        assert settings.visual_duplicate_min_duration_ms == 2000
        assert settings.visual_duplicate_gap_tolerance_ms == 1500

    def test_no_conflict_with_existing_settings(self):
        """Test that visual duplicate settings don't conflict with existing fields."""
        settings = Settings(
            plex_url="http://localhost:32400",
            detection_method="visual_duplicates",
            visual_duplicate_detection_enabled=True,
            confidence_threshold=0.8,
            min_segment_duration_ms=3000,
        )

        assert settings.plex_url == "http://localhost:32400"
        assert settings.detection_method == "visual_duplicates"
        assert settings.confidence_threshold == 0.8
        assert settings.min_segment_duration_ms == 3000
