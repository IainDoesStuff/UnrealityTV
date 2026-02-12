"""Caching system for UnrealityTV processing."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Exception raised when cache operations fail."""

    pass


class CacheConfig(BaseModel):
    """Configuration for cache system.

    Attributes:
        enabled: Whether caching is enabled
        cache_dir: Directory where cache files are stored
        ttl_seconds: Time-to-live for cache entries in seconds
        max_cache_size_mb: Maximum cache size in megabytes
    """

    enabled: bool = Field(default=True, description="Enable caching")
    cache_dir: Path = Field(
        default_factory=lambda: Path.home() / ".cache" / "unrealitytv",
        description="Cache directory path",
    )
    ttl_seconds: int = Field(
        default=86400,
        ge=0,
        description="Time-to-live for cache entries in seconds (24 hours default)",
    )
    max_cache_size_mb: int = Field(
        default=500, ge=1, description="Maximum cache size in MB"
    )

    model_config = {"json_encoders": {Path: str}}


class CacheManager:
    """Manages cache operations with TTL and size limits.

    Provides methods to store, retrieve, and manage cached values.
    Automatically handles expiration and cleanup when cache exceeds max size.
    """

    def __init__(self, config: Optional[CacheConfig] = None) -> None:
        """Initialize cache manager.

        Args:
            config: Cache configuration (uses defaults if None)
        """
        self.config = config or CacheConfig()
        self._ensure_cache_dir()
        logger.info(f"Initialized CacheManager with cache_dir={self.config.cache_dir}")

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists.

        Raises:
            CacheError: If directory creation fails
        """
        try:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Cache directory ready: {self.config.cache_dir}")
        except Exception as e:
            msg = f"Failed to create cache directory: {e}"
            logger.error(msg)
            raise CacheError(msg) from e

    def _get_cache_file(self, key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        # Sanitize key to valid filename
        safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return self.config.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[dict]:
        """Retrieve value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value dict or None if not found/expired
        """
        if not self.config.enabled:
            return None

        try:
            cache_file = self._get_cache_file(key)
            if not cache_file.exists():
                logger.debug(f"Cache miss for key: {key}")
                return None

            with open(cache_file, "r") as f:
                data = json.load(f)

            # Check expiration
            timestamp = data.get("timestamp", 0)
            age_seconds = time.time() - timestamp

            if age_seconds > self.config.ttl_seconds:
                logger.debug(f"Cache expired for key: {key}")
                cache_file.unlink(missing_ok=True)
                return None

            logger.debug(f"Cache hit for key: {key}")
            return data.get("value")
        except Exception as e:
            logger.warning(f"Error retrieving cache for {key}: {e}")
            return None

    def set(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be dict)
            ttl: Optional override for TTL in seconds

        Raises:
            CacheError: If write fails
        """
        if not self.config.enabled:
            return

        try:
            self._ensure_cache_dir()
            cache_file = self._get_cache_file(key)

            data = {
                "value": value,
                "timestamp": time.time(),
                "ttl": ttl or self.config.ttl_seconds,
            }

            with open(cache_file, "w") as f:
                json.dump(data, f, default=str)  # Handle Path and other non-JSON types

            logger.debug(f"Cached value for key: {key}")

            # Check if cleanup needed
            if self.get_cache_size() > self.config.max_cache_size_mb:
                self.cleanup_expired()
        except Exception as e:
            msg = f"Failed to cache value for {key}: {e}"
            logger.error(msg)
            raise CacheError(msg) from e

    def delete(self, key: str) -> None:
        """Delete cache entry.

        Args:
            key: Cache key
        """
        try:
            cache_file = self._get_cache_file(key)
            cache_file.unlink(missing_ok=True)
            logger.debug(f"Deleted cache entry: {key}")
        except Exception as e:
            logger.warning(f"Error deleting cache for {key}: {e}")

    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            if self.config.cache_dir.exists():
                for file in self.config.cache_dir.glob("*.json"):
                    file.unlink(missing_ok=True)
            logger.info("Cleared all cache entries")
        except Exception as e:
            logger.warning(f"Error clearing cache: {e}")

    def cleanup_expired(self) -> None:
        """Remove expired cache entries.

        Iterates through all cache files and removes those
        whose TTL has expired.
        """
        try:
            current_time = time.time()
            removed_count = 0

            if not self.config.cache_dir.exists():
                return

            for cache_file in self.config.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)

                    timestamp = data.get("timestamp", 0)
                    age_seconds = current_time - timestamp
                    ttl = data.get("ttl", self.config.ttl_seconds)

                    if age_seconds > ttl:
                        cache_file.unlink(missing_ok=True)
                        removed_count += 1
                except Exception as e:
                    logger.debug(f"Error checking cache file {cache_file}: {e}")

            logger.info(f"Cleaned up {removed_count} expired cache entries")
        except Exception as e:
            logger.warning(f"Error during cache cleanup: {e}")

    def get_cache_size(self) -> float:
        """Get total cache size in MB.

        Returns:
            Cache size in megabytes
        """
        try:
            if not self.config.cache_dir.exists():
                return 0.0

            total_bytes = sum(
                f.stat().st_size for f in self.config.cache_dir.glob("*.json")
            )
            size_mb = total_bytes / (1024 * 1024)
            logger.debug(f"Cache size: {size_mb:.2f} MB")
            return size_mb
        except Exception as e:
            logger.warning(f"Error calculating cache size: {e}")
            return 0.0
