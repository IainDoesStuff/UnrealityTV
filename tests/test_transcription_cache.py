"""Tests for transcription caching."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.cache import CacheConfig
from unrealitytv.transcription.cache import CachingWhisperTranscriber
from unrealitytv.transcription.whisper import TranscriptSegment


class TestCachingWhisperTranscriber:
    """Tests for CachingWhisperTranscriber."""

    @pytest.fixture
    def temp_audio(self, tmp_path: Path) -> Path:
        """Create temporary audio file."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
        return audio_file

    @pytest.fixture
    def cache_config(self, tmp_path: Path) -> CacheConfig:
        """Create cache config with temp directory."""
        return CacheConfig(cache_dir=tmp_path / "cache")

    @pytest.fixture
    def transcriber(self, cache_config: CacheConfig) -> CachingWhisperTranscriber:
        """Create caching transcriber."""
        return CachingWhisperTranscriber(use_cache=True, cache_config=cache_config)

    def test_init_with_cache_enabled(self, cache_config: CacheConfig) -> None:
        """Test initialization with caching enabled."""
        transcriber = CachingWhisperTranscriber(use_cache=True, cache_config=cache_config)

        assert transcriber.use_cache is True
        assert transcriber.cache_manager is not None
        assert transcriber.cache_manager.config.enabled is True

    def test_init_with_cache_disabled(self, cache_config: CacheConfig) -> None:
        """Test initialization with caching disabled."""
        transcriber = CachingWhisperTranscriber(
            use_cache=False, cache_config=cache_config
        )

        assert transcriber.use_cache is False
        assert transcriber.cache_manager is not None

    def test_make_cache_key(self, transcriber: CachingWhisperTranscriber, temp_audio: Path) -> None:
        """Test cache key generation."""
        language = "en"
        expected_hash = hashlib.md5(str(temp_audio).encode()).hexdigest()
        expected_key = f"transcription_{expected_hash}_en"

        key = transcriber._make_cache_key(temp_audio, language)

        assert key == expected_key

    def test_make_cache_key_different_languages(
        self, transcriber: CachingWhisperTranscriber, temp_audio: Path
    ) -> None:
        """Test cache keys differ for different languages."""
        key_en = transcriber._make_cache_key(temp_audio, "en")
        key_fr = transcriber._make_cache_key(temp_audio, "fr")

        assert key_en != key_fr
        assert "en" in key_en
        assert "fr" in key_fr

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_cache_hit(
        self, mock_super: MagicMock, transcriber: CachingWhisperTranscriber, temp_audio: Path
    ) -> None:
        """Test cache hit returns cached result without calling transcriber."""
        # Pre-populate cache
        segments = [
            TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Hello"),
            TranscriptSegment(start_time_ms=1000, end_time_ms=2000, text="World"),
        ]
        cache_key = transcriber._make_cache_key(temp_audio, "auto")
        cache_data = [seg.model_dump() for seg in segments]
        transcriber.cache_manager.set(cache_key, cache_data)

        # Transcribe should return cached data
        result = transcriber.transcribe(temp_audio)

        assert len(result) == 2
        assert result[0].text == "Hello"
        assert result[1].text == "World"
        mock_super.assert_not_called()

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_cache_miss(
        self,
        mock_super: MagicMock,
        transcriber: CachingWhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """Test cache miss calls parent transcriber and caches result."""
        # Mock parent transcriber
        segments = [TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Hello")]
        mock_super.return_value = segments

        result = transcriber.transcribe(temp_audio)

        assert len(result) == 1
        assert result[0].text == "Hello"
        mock_super.assert_called_once()

        # Verify it was cached
        cache_key = transcriber._make_cache_key(temp_audio, "auto")
        cached = transcriber.cache_manager.get(cache_key)
        assert cached is not None
        assert cached[0]["text"] == "Hello"

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_with_language(
        self,
        mock_super: MagicMock,
        transcriber: CachingWhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """Test transcription with specific language."""
        segments = [TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Bonjour")]
        mock_super.return_value = segments

        result = transcriber.transcribe(temp_audio, language="fr")

        assert len(result) == 1
        mock_super.assert_called_once_with(temp_audio, "fr")

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_cache_disabled(
        self,
        mock_super: MagicMock,
        cache_config: CacheConfig,
        temp_audio: Path,
    ) -> None:
        """Test transcription with caching disabled."""
        transcriber = CachingWhisperTranscriber(
            use_cache=False, cache_config=cache_config
        )

        segments = [TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Hello")]
        mock_super.return_value = segments

        result = transcriber.transcribe(temp_audio)

        assert len(result) == 1

        # Verify nothing was cached
        cache_key = transcriber._make_cache_key(temp_audio, "auto")
        cached = transcriber.cache_manager.get(cache_key)
        assert cached is None

    def test_clear_cache(self, transcriber: CachingWhisperTranscriber, temp_audio: Path) -> None:
        """Test clearing transcription cache."""
        # Add items to cache
        cache_key = transcriber._make_cache_key(temp_audio, "en")
        transcriber.cache_manager.set(
            cache_key, [{"start_time_ms": 0, "end_time_ms": 1000, "text": "Test"}]
        )

        assert transcriber.cache_manager.get(cache_key) is not None

        transcriber.clear_cache()

        assert transcriber.cache_manager.get(cache_key) is None

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_cache_isolation(
        self,
        mock_super: MagicMock,
        transcriber: CachingWhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """Test that different languages have separate cache entries."""
        en_segments = [
            TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Hello")
        ]
        fr_segments = [
            TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Bonjour")
        ]

        mock_super.side_effect = [en_segments, fr_segments]

        # First call in English
        result_en = transcriber.transcribe(temp_audio, language="en")
        assert result_en[0].text == "Hello"

        # Second call in French
        result_fr = transcriber.transcribe(temp_audio, language="fr")
        assert result_fr[0].text == "Bonjour"

        # Both should have been called
        assert mock_super.call_count == 2

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_multiple_files(
        self,
        mock_super: MagicMock,
        transcriber: CachingWhisperTranscriber,
        tmp_path: Path,
    ) -> None:
        """Test transcribing multiple files with separate caches."""
        file1 = tmp_path / "file1.wav"
        file2 = tmp_path / "file2.wav"
        file1.write_bytes(b"RIFF" + b"\x00" * 100)
        file2.write_bytes(b"RIFF" + b"\x11" * 100)

        segments1 = [
            TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="First")
        ]
        segments2 = [
            TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Second")
        ]

        mock_super.side_effect = [segments1, segments2]

        result1 = transcriber.transcribe(file1)
        result2 = transcriber.transcribe(file2)

        assert result1[0].text == "First"
        assert result2[0].text == "Second"

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_empty_result(
        self,
        mock_super: MagicMock,
        transcriber: CachingWhisperTranscriber,
        temp_audio: Path,
    ) -> None:
        """Test transcribing file with no segments."""
        mock_super.return_value = []

        result = transcriber.transcribe(temp_audio)

        assert result == []

        # Verify empty result was cached
        cache_key = transcriber._make_cache_key(temp_audio, "auto")
        cached = transcriber.cache_manager.get(cache_key)
        assert cached == []

    @patch("unrealitytv.transcription.whisper.WhisperTranscriber.transcribe")
    def test_transcribe_cache_persistence(
        self,
        mock_super: MagicMock,
        tmp_path: Path,
        temp_audio: Path,
    ) -> None:
        """Test cache persists across transcriber instances."""
        cache_config = CacheConfig(cache_dir=tmp_path / "cache")
        transcriber1 = CachingWhisperTranscriber(cache_config=cache_config)

        segments = [TranscriptSegment(start_time_ms=0, end_time_ms=1000, text="Hello")]
        mock_super.return_value = segments

        # First transcriber transcribes
        result1 = transcriber1.transcribe(temp_audio)
        assert len(result1) == 1

        # Second transcriber with same cache dir should hit cache
        transcriber2 = CachingWhisperTranscriber(cache_config=cache_config)
        result2 = transcriber2.transcribe(temp_audio)

        assert len(result2) == 1
        assert result2[0].text == "Hello"
        # Parent should only be called once
        assert mock_super.call_count == 1
