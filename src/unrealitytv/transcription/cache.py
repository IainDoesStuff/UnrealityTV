"""Caching for Whisper transcription results."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

from unrealitytv.cache import CacheConfig, CacheManager
from unrealitytv.transcription.whisper import TranscriptSegment, WhisperTranscriber

logger = logging.getLogger(__name__)


class TranscriptionCacheError(Exception):
    """Exception raised when transcription caching fails."""

    pass


class CachingWhisperTranscriber(WhisperTranscriber):
    """WhisperTranscriber with caching support.

    Caches transcription results by file hash and language to avoid
    reprocessing the same audio files. Cache hits provide 10-100x
    speedup by skipping actual transcription.

    Attributes:
        gpu_enabled: Whether to use GPU for transcription
        use_cache: Whether caching is enabled
        cache_manager: CacheManager instance for cache operations
    """

    def __init__(
        self,
        gpu_enabled: bool = False,
        use_cache: bool = True,
        cache_config: Optional[CacheConfig] = None,
    ) -> None:
        """Initialize caching transcriber.

        Args:
            gpu_enabled: Whether to use GPU for transcription
            use_cache: Whether to use caching
            cache_config: Optional cache configuration
        """
        super().__init__(gpu_enabled=gpu_enabled)
        self.use_cache = use_cache
        self.cache_manager = CacheManager(cache_config or CacheConfig())
        logger.info(f"Initialized CachingWhisperTranscriber with use_cache={use_cache}")

    def _make_cache_key(self, file_path: Path, language: str) -> str:
        """Generate cache key from file path and language.

        Uses MD5 hash of file path to create unique key.

        Args:
            file_path: Path to audio file
            language: Language code

        Returns:
            Cache key string
        """
        file_hash = hashlib.md5(str(file_path).encode()).hexdigest()
        return f"transcription_{file_hash}_{language}"

    def transcribe(
        self, file_path: Path, language: Optional[str] = None
    ) -> list[TranscriptSegment]:
        """Transcribe audio file with caching.

        First checks cache for existing transcription. If found and not expired,
        returns cached result. Otherwise, performs transcription and caches result.

        Args:
            file_path: Path to audio file
            language: Optional language code (default: "auto")

        Returns:
            List of transcript segments

        Raises:
            TranscriptionCacheError: If caching operations fail
        """
        lang = language or "auto"
        cache_key = self._make_cache_key(file_path, lang)

        # Try to get from cache
        if self.use_cache:
            try:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.info(
                        f"Cache hit for transcription of {file_path.name} [{lang}]"
                    )
                    return [TranscriptSegment(**seg) for seg in cached_result]
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")

        # Perform transcription
        logger.debug(f"Transcribing {file_path.name} (cache miss or caching disabled)")
        segments = super().transcribe(file_path, language)

        # Store in cache
        if self.use_cache:
            try:
                cache_data = [seg.model_dump() for seg in segments]
                self.cache_manager.set(cache_key, cache_data)
                logger.debug(f"Cached transcription for {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to cache transcription: {e}")

        return segments

    def clear_cache(self) -> None:
        """Clear all transcription cache entries."""
        try:
            self.cache_manager.clear()
            logger.info("Cleared transcription cache")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
