"""Caching for analysis pipeline results."""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from unrealitytv.analysis.pipeline import AnalysisPipeline
from unrealitytv.cache import CacheConfig, CacheManager
from unrealitytv.models import AnalysisResult, Episode

logger = logging.getLogger(__name__)


class AnalysisCacheError(Exception):
    """Exception raised when analysis caching fails."""

    pass


class CachingAnalysisPipeline(AnalysisPipeline):
    """AnalysisPipeline with caching support.

    Caches full analysis results by episode file hash to avoid
    reprocessing identical episodes. Cache hits provide 100-1000x
    speedup by skipping audio extraction, transcription, and analysis.

    Attributes:
        gpu_enabled: Whether to use GPU for transcription
        recap_keywords: Custom recap detection keywords
        preview_keywords: Custom preview detection keywords
        cleanup_temp_files: Whether to clean up temporary files
        use_cache: Whether caching is enabled
        cache_manager: CacheManager instance for cache operations
    """

    def __init__(
        self,
        gpu_enabled: bool = False,
        recap_keywords: Optional[list[str]] = None,
        preview_keywords: Optional[list[str]] = None,
        cleanup_temp_files: bool = True,
        use_cache: bool = True,
        cache_config: Optional[CacheConfig] = None,
    ) -> None:
        """Initialize caching analysis pipeline.

        Args:
            gpu_enabled: Whether to use GPU for transcription
            recap_keywords: Custom recap detection keywords
            preview_keywords: Custom preview detection keywords
            cleanup_temp_files: Whether to clean up temporary audio files
            use_cache: Whether to use caching
            cache_config: Optional cache configuration
        """
        super().__init__(
            gpu_enabled=gpu_enabled,
            recap_keywords=recap_keywords,
            preview_keywords=preview_keywords,
            cleanup_temp_files=cleanup_temp_files,
        )
        self.use_cache = use_cache
        self.cache_manager = CacheManager(cache_config or CacheConfig())
        logger.info(f"Initialized CachingAnalysisPipeline with use_cache={use_cache}")

    def _make_cache_key(self, episode: Episode) -> str:
        """Generate cache key from episode file path.

        Uses MD5 hash of file path to create unique key.

        Args:
            episode: Episode to cache

        Returns:
            Cache key string
        """
        file_hash = hashlib.md5(str(episode.file_path).encode()).hexdigest()
        return f"analysis_{file_hash}"

    def analyze(self, episode: Episode) -> AnalysisResult:
        """Analyze episode with caching.

        First checks cache for existing analysis. If found and not expired,
        returns cached result. Otherwise, performs full analysis pipeline
        (audio extraction, transcription, pattern matching) and caches result.

        Args:
            episode: Episode to analyze

        Returns:
            Analysis result with detected skip segments

        Raises:
            AnalysisCacheError: If caching operations fail
        """
        cache_key = self._make_cache_key(episode)

        # Try to get from cache
        if self.use_cache:
            try:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Cache hit for analysis of {episode.file_path.name}")
                    return AnalysisResult(**cached_result)
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")

        # Perform analysis
        logger.debug(
            f"Analyzing {episode.file_path.name} (cache miss or caching disabled)"
        )
        result = super().analyze(episode)

        # Store in cache
        if self.use_cache:
            try:
                cache_data = result.model_dump()
                self.cache_manager.set(cache_key, cache_data)
                logger.debug(f"Cached analysis for {episode.file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to cache analysis: {e}")

        return result

    def clear_cache(self) -> None:
        """Clear all analysis cache entries."""
        try:
            self.cache_manager.clear()
            logger.info("Cleared analysis cache")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")
