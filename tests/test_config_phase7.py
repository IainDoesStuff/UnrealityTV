"""Tests for Phase 7 configuration enhancements."""

from __future__ import annotations

import pytest

from unrealitytv.config import Settings


class TestPhase7ConfigDefaults:
    """Test Phase 7 configuration defaults."""

    def test_silence_detection_disabled_by_default(self) -> None:
        """Test that silence detection is disabled by default."""
        settings = Settings()
        assert settings.silence_detection_enabled is False

    def test_silence_threshold_default(self) -> None:
        """Test default silence threshold."""
        settings = Settings()
        assert settings.silence_threshold_db == -60.0

    def test_silence_min_duration_default(self) -> None:
        """Test default minimum silence duration."""
        settings = Settings()
        assert settings.silence_min_duration_ms == 500

    def test_credits_detection_disabled_by_default(self) -> None:
        """Test that credits detection is disabled by default."""
        settings = Settings()
        assert settings.credits_detection_enabled is False

    def test_credits_threshold_default(self) -> None:
        """Test default credits detection threshold."""
        settings = Settings()
        assert settings.credits_threshold == 0.7

    def test_credits_min_duration_default(self) -> None:
        """Test default minimum credits duration."""
        settings = Settings()
        assert settings.credits_min_duration_ms == 5000

    def test_combined_detection_enabled_by_default(self) -> None:
        """Test that combined detection is allowed by default."""
        settings = Settings()
        assert settings.allow_combined_detection is True


class TestPhase7ConfigCustomization:
    """Test Phase 7 configuration customization."""

    def test_silence_detection_enabled(self) -> None:
        """Test enabling silence detection."""
        settings = Settings(silence_detection_enabled=True)
        assert settings.silence_detection_enabled is True

    def test_silence_threshold_custom(self) -> None:
        """Test custom silence threshold."""
        settings = Settings(silence_threshold_db=-50.0)
        assert settings.silence_threshold_db == -50.0

    def test_silence_min_duration_custom(self) -> None:
        """Test custom silence minimum duration."""
        settings = Settings(silence_min_duration_ms=1000)
        assert settings.silence_min_duration_ms == 1000

    def test_credits_detection_enabled(self) -> None:
        """Test enabling credits detection."""
        settings = Settings(credits_detection_enabled=True)
        assert settings.credits_detection_enabled is True

    def test_credits_threshold_custom(self) -> None:
        """Test custom credits threshold."""
        settings = Settings(credits_threshold=0.5)
        assert settings.credits_threshold == 0.5

    def test_credits_min_duration_custom(self) -> None:
        """Test custom credits minimum duration."""
        settings = Settings(credits_min_duration_ms=10000)
        assert settings.credits_min_duration_ms == 10000

    def test_combined_detection_disabled(self) -> None:
        """Test disabling combined detection."""
        settings = Settings(allow_combined_detection=False)
        assert settings.allow_combined_detection is False


class TestPhase7ConfigValidation:
    """Test Phase 7 configuration validation."""

    def test_silence_threshold_valid_range(self) -> None:
        """Test that silence threshold accepts valid values."""
        # Negative dB values are valid
        settings = Settings(silence_threshold_db=-60.0)
        assert settings.silence_threshold_db == -60.0

        settings = Settings(silence_threshold_db=-30.0)
        assert settings.silence_threshold_db == -30.0

        # Zero dB is valid
        settings = Settings(silence_threshold_db=0.0)
        assert settings.silence_threshold_db == 0.0

    def test_silence_min_duration_non_negative(self) -> None:
        """Test that silence min duration is non-negative."""
        settings = Settings(silence_min_duration_ms=0)
        assert settings.silence_min_duration_ms == 0

        settings = Settings(silence_min_duration_ms=500)
        assert settings.silence_min_duration_ms == 500

    def test_silence_min_duration_rejects_negative(self) -> None:
        """Test that silence min duration rejects negative values."""
        with pytest.raises(ValueError):
            Settings(silence_min_duration_ms=-100)

    def test_credits_threshold_valid_range(self) -> None:
        """Test that credits threshold is between 0 and 1."""
        settings = Settings(credits_threshold=0.0)
        assert settings.credits_threshold == 0.0

        settings = Settings(credits_threshold=0.5)
        assert settings.credits_threshold == 0.5

        settings = Settings(credits_threshold=1.0)
        assert settings.credits_threshold == 1.0

    def test_credits_threshold_rejects_out_of_range(self) -> None:
        """Test that credits threshold rejects out-of-range values."""
        with pytest.raises(ValueError):
            Settings(credits_threshold=-0.1)

        with pytest.raises(ValueError):
            Settings(credits_threshold=1.1)

    def test_credits_min_duration_non_negative(self) -> None:
        """Test that credits min duration is non-negative."""
        settings = Settings(credits_min_duration_ms=0)
        assert settings.credits_min_duration_ms == 0

        settings = Settings(credits_min_duration_ms=5000)
        assert settings.credits_min_duration_ms == 5000

    def test_credits_min_duration_rejects_negative(self) -> None:
        """Test that credits min duration rejects negative values."""
        with pytest.raises(ValueError):
            Settings(credits_min_duration_ms=-1000)


class TestPhase7DetectionMethodValidation:
    """Test detection method validation with Phase 7 methods."""

    def test_detection_method_silence(self) -> None:
        """Test silence detection method is valid."""
        settings = Settings(detection_method="silence")
        assert settings.detection_method == "silence"

    def test_detection_method_credits(self) -> None:
        """Test credits detection method is valid."""
        settings = Settings(detection_method="credits")
        assert settings.detection_method == "credits"

    def test_detection_method_hybrid_extended(self) -> None:
        """Test hybrid_extended detection method is valid."""
        settings = Settings(detection_method="hybrid_extended")
        assert settings.detection_method == "hybrid_extended"

    def test_detection_method_preserves_existing(self) -> None:
        """Test that existing methods still work."""
        for method in ["scene_detect", "transnetv2", "hybrid", "auto"]:
            settings = Settings(detection_method=method)
            assert settings.detection_method == method

    def test_detection_method_invalid(self) -> None:
        """Test that invalid detection methods are rejected."""
        with pytest.raises(ValueError):
            Settings(detection_method="invalid_method")

        with pytest.raises(ValueError):
            Settings(detection_method="silence_detection")  # Wrong name


class TestPhase7ConfigCombinations:
    """Test combinations of Phase 7 settings."""

    def test_both_silence_and_credits_enabled(self) -> None:
        """Test enabling both silence and credits detection."""
        settings = Settings(
            silence_detection_enabled=True,
            credits_detection_enabled=True,
        )
        assert settings.silence_detection_enabled is True
        assert settings.credits_detection_enabled is True

    def test_both_detections_with_custom_thresholds(self) -> None:
        """Test custom thresholds for both methods."""
        settings = Settings(
            silence_detection_enabled=True,
            silence_threshold_db=-50.0,
            silence_min_duration_ms=1000,
            credits_detection_enabled=True,
            credits_threshold=0.5,
            credits_min_duration_ms=8000,
        )
        assert settings.silence_threshold_db == -50.0
        assert settings.silence_min_duration_ms == 1000
        assert settings.credits_threshold == 0.5
        assert settings.credits_min_duration_ms == 8000

    def test_hybrid_extended_with_all_phase7_settings(self) -> None:
        """Test hybrid_extended method with all Phase 7 settings."""
        settings = Settings(
            detection_method="hybrid_extended",
            silence_detection_enabled=True,
            credits_detection_enabled=True,
            allow_combined_detection=True,
        )
        assert settings.detection_method == "hybrid_extended"
        assert settings.silence_detection_enabled is True
        assert settings.credits_detection_enabled is True
        assert settings.allow_combined_detection is True

    def test_phase7_with_existing_settings(self) -> None:
        """Test Phase 7 settings don't interfere with existing settings."""
        settings = Settings(
            plex_url="http://plex.local:32400",
            confidence_threshold=0.8,
            enable_caching=True,
            silence_detection_enabled=True,
            credits_detection_enabled=True,
        )
        assert settings.plex_url == "http://plex.local:32400"
        assert settings.confidence_threshold == 0.8
        assert settings.enable_caching is True
        assert settings.silence_detection_enabled is True
        assert settings.credits_detection_enabled is True


class TestPhase7ConfigEnvVariables:
    """Test Phase 7 configuration via environment variables."""

    def test_silence_detection_from_env(self, monkeypatch) -> None:
        """Test reading silence detection from environment."""
        monkeypatch.setenv("SILENCE_DETECTION_ENABLED", "true")
        settings = Settings()
        assert settings.silence_detection_enabled is True

    def test_silence_threshold_from_env(self, monkeypatch) -> None:
        """Test reading silence threshold from environment."""
        monkeypatch.setenv("SILENCE_THRESHOLD_DB", "-50")
        settings = Settings()
        assert settings.silence_threshold_db == -50.0

    def test_silence_min_duration_from_env(self, monkeypatch) -> None:
        """Test reading silence min duration from environment."""
        monkeypatch.setenv("SILENCE_MIN_DURATION_MS", "1000")
        settings = Settings()
        assert settings.silence_min_duration_ms == 1000

    def test_credits_detection_from_env(self, monkeypatch) -> None:
        """Test reading credits detection from environment."""
        monkeypatch.setenv("CREDITS_DETECTION_ENABLED", "true")
        settings = Settings()
        assert settings.credits_detection_enabled is True

    def test_credits_threshold_from_env(self, monkeypatch) -> None:
        """Test reading credits threshold from environment."""
        monkeypatch.setenv("CREDITS_THRESHOLD", "0.5")
        settings = Settings()
        assert settings.credits_threshold == 0.5

    def test_credits_min_duration_from_env(self, monkeypatch) -> None:
        """Test reading credits min duration from environment."""
        monkeypatch.setenv("CREDITS_MIN_DURATION_MS", "8000")
        settings = Settings()
        assert settings.credits_min_duration_ms == 8000

    def test_allow_combined_detection_from_env(self, monkeypatch) -> None:
        """Test reading combined detection flag from environment."""
        monkeypatch.setenv("ALLOW_COMBINED_DETECTION", "false")
        settings = Settings()
        assert settings.allow_combined_detection is False
