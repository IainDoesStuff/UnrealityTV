"""Tests for enhanced configuration system."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from unrealitytv.config import Settings


class TestSettingsBasic:
    """Test basic settings initialization."""

    def test_default_settings(self) -> None:
        """Test that default settings are applied correctly."""
        settings = Settings()
        assert settings.plex_url == "http://localhost:32400"
        assert settings.plex_token == ""
        assert settings.watch_dir == Path(".")
        assert settings.database_path == Path("unrealitytv.db")
        assert settings.gpu_enabled is False

    def test_default_phase5_settings(self) -> None:
        """Test default Phase 5 settings."""
        settings = Settings()
        assert settings.skip_segment_types == []
        assert settings.confidence_threshold == 0.7
        assert settings.min_segment_duration_ms == 3000
        assert settings.detection_method == "auto"
        assert settings.enable_plex_application is False
        assert settings.batch_processing is False


class TestSkipSegmentTypes:
    """Test skip_segment_types field."""

    def test_empty_skip_segment_types(self) -> None:
        """Test empty skip segment types."""
        settings = Settings(skip_segment_types=[])
        assert settings.skip_segment_types == []

    def test_single_skip_segment_type(self) -> None:
        """Test single skip segment type."""
        settings = Settings(skip_segment_types=["recap"])
        assert settings.skip_segment_types == ["recap"]

    def test_multiple_skip_segment_types(self) -> None:
        """Test multiple skip segment types."""
        settings = Settings(skip_segment_types=["recap", "preview", "filler"])
        assert settings.skip_segment_types == ["recap", "preview", "filler"]

    def test_skip_segment_types_from_comma_separated_string(self) -> None:
        """Test parsing skip_segment_types from comma-separated string."""
        settings = Settings(skip_segment_types="recap, preview, filler")
        assert settings.skip_segment_types == ["recap", "preview", "filler"]

    def test_skip_segment_types_from_string_with_whitespace(self) -> None:
        """Test parsing with extra whitespace."""
        settings = Settings(skip_segment_types="  recap  ,  preview  ")
        assert settings.skip_segment_types == ["recap", "preview"]


class TestConfidenceThreshold:
    """Test confidence_threshold field."""

    def test_default_confidence_threshold(self) -> None:
        """Test default confidence threshold."""
        settings = Settings()
        assert settings.confidence_threshold == 0.7

    def test_custom_confidence_threshold(self) -> None:
        """Test custom confidence threshold."""
        settings = Settings(confidence_threshold=0.85)
        assert settings.confidence_threshold == 0.85

    def test_confidence_threshold_zero(self) -> None:
        """Test confidence threshold at lower bound."""
        settings = Settings(confidence_threshold=0.0)
        assert settings.confidence_threshold == 0.0

    def test_confidence_threshold_one(self) -> None:
        """Test confidence threshold at upper bound."""
        settings = Settings(confidence_threshold=1.0)
        assert settings.confidence_threshold == 1.0

    def test_confidence_threshold_below_zero(self) -> None:
        """Test confidence threshold below minimum raises error."""
        with pytest.raises(ValidationError):
            Settings(confidence_threshold=-0.1)

    def test_confidence_threshold_above_one(self) -> None:
        """Test confidence threshold above maximum raises error."""
        with pytest.raises(ValidationError):
            Settings(confidence_threshold=1.1)

    def test_confidence_threshold_invalid_type(self) -> None:
        """Test confidence threshold with invalid type."""
        with pytest.raises(ValidationError):
            Settings(confidence_threshold="not a number")


class TestMinSegmentDuration:
    """Test min_segment_duration_ms field."""

    def test_default_min_segment_duration(self) -> None:
        """Test default minimum segment duration."""
        settings = Settings()
        assert settings.min_segment_duration_ms == 3000

    def test_custom_min_segment_duration(self) -> None:
        """Test custom minimum segment duration."""
        settings = Settings(min_segment_duration_ms=5000)
        assert settings.min_segment_duration_ms == 5000

    def test_min_segment_duration_zero(self) -> None:
        """Test minimum segment duration at lower bound."""
        settings = Settings(min_segment_duration_ms=0)
        assert settings.min_segment_duration_ms == 0

    def test_min_segment_duration_negative(self) -> None:
        """Test negative minimum segment duration raises error."""
        with pytest.raises(ValidationError):
            Settings(min_segment_duration_ms=-1)

    def test_min_segment_duration_large_value(self) -> None:
        """Test large minimum segment duration."""
        settings = Settings(min_segment_duration_ms=60000)
        assert settings.min_segment_duration_ms == 60000

    def test_min_segment_duration_invalid_type(self) -> None:
        """Test minimum segment duration with invalid type."""
        with pytest.raises(ValidationError):
            Settings(min_segment_duration_ms="not a number")


class TestDetectionMethod:
    """Test detection_method field."""

    def test_default_detection_method(self) -> None:
        """Test default detection method."""
        settings = Settings()
        assert settings.detection_method == "auto"

    def test_scene_detect_method(self) -> None:
        """Test scene_detect method."""
        settings = Settings(detection_method="scene_detect")
        assert settings.detection_method == "scene_detect"

    def test_transnetv2_method(self) -> None:
        """Test transnetv2 method."""
        settings = Settings(detection_method="transnetv2")
        assert settings.detection_method == "transnetv2"

    def test_hybrid_method(self) -> None:
        """Test hybrid method."""
        settings = Settings(detection_method="hybrid")
        assert settings.detection_method == "hybrid"

    def test_auto_method(self) -> None:
        """Test auto method."""
        settings = Settings(detection_method="auto")
        assert settings.detection_method == "auto"

    def test_invalid_detection_method(self) -> None:
        """Test invalid detection method raises error."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(detection_method="invalid_method")
        assert "detection_method must be one of" in str(exc_info.value)

    def test_detection_method_case_sensitive(self) -> None:
        """Test that detection method is case sensitive."""
        with pytest.raises(ValidationError):
            Settings(detection_method="AUTO")


class TestPlexApplication:
    """Test enable_plex_application field."""

    def test_default_plex_application_disabled(self) -> None:
        """Test Plex application is disabled by default."""
        settings = Settings()
        assert settings.enable_plex_application is False

    def test_enable_plex_application(self) -> None:
        """Test enabling Plex application."""
        settings = Settings(enable_plex_application=True)
        assert settings.enable_plex_application is True

    def test_disable_plex_application(self) -> None:
        """Test explicitly disabling Plex application."""
        settings = Settings(enable_plex_application=False)
        assert settings.enable_plex_application is False


class TestBatchProcessing:
    """Test batch_processing field."""

    def test_default_batch_processing_disabled(self) -> None:
        """Test batch processing is disabled by default."""
        settings = Settings()
        assert settings.batch_processing is False

    def test_enable_batch_processing(self) -> None:
        """Test enabling batch processing."""
        settings = Settings(batch_processing=True)
        assert settings.batch_processing is True

    def test_disable_batch_processing(self) -> None:
        """Test explicitly disabling batch processing."""
        settings = Settings(batch_processing=False)
        assert settings.batch_processing is False


class TestComplexConfigurations:
    """Test complex configuration combinations."""

    def test_full_configuration(self) -> None:
        """Test setting all configuration options."""
        settings = Settings(
            plex_url="http://192.168.1.100:32400",
            plex_token="abc123def456",
            watch_dir=Path("/media/tv"),
            database_path=Path("/var/lib/unrealitytv.db"),
            gpu_enabled=True,
            skip_segment_types=["recap", "preview"],
            confidence_threshold=0.8,
            min_segment_duration_ms=2000,
            detection_method="hybrid",
            enable_plex_application=True,
            batch_processing=True,
        )

        assert settings.plex_url == "http://192.168.1.100:32400"
        assert settings.plex_token == "abc123def456"
        assert settings.watch_dir == Path("/media/tv")
        assert settings.database_path == Path("/var/lib/unrealitytv.db")
        assert settings.gpu_enabled is True
        assert settings.skip_segment_types == ["recap", "preview"]
        assert settings.confidence_threshold == 0.8
        assert settings.min_segment_duration_ms == 2000
        assert settings.detection_method == "hybrid"
        assert settings.enable_plex_application is True
        assert settings.batch_processing is True

    def test_minimal_valid_configuration(self) -> None:
        """Test minimal valid configuration with only necessary overrides."""
        settings = Settings(
            confidence_threshold=0.5,
            min_segment_duration_ms=1000,
        )

        assert settings.confidence_threshold == 0.5
        assert settings.min_segment_duration_ms == 1000
        # Other fields should have defaults
        assert settings.detection_method == "auto"
        assert settings.enable_plex_application is False
