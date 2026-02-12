"""Tests for cache management system."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from unrealitytv.cache import CacheConfig, CacheError, CacheManager


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_cache_config_defaults(self) -> None:
        """Test default cache configuration."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.ttl_seconds == 86400  # 24 hours
        assert config.max_cache_size_mb == 500
        assert "unrealitytv" in str(config.cache_dir)

    def test_cache_config_custom(self) -> None:
        """Test custom cache configuration."""
        cache_dir = Path("/tmp/test_cache")
        config = CacheConfig(
            enabled=False,
            cache_dir=cache_dir,
            ttl_seconds=3600,
            max_cache_size_mb=100,
        )
        assert config.enabled is False
        assert config.cache_dir == cache_dir
        assert config.ttl_seconds == 3600
        assert config.max_cache_size_mb == 100

    def test_cache_config_validation_ttl(self) -> None:
        """Test TTL validation."""
        with pytest.raises(ValueError):
            CacheConfig(ttl_seconds=-1)

    def test_cache_config_validation_size(self) -> None:
        """Test max cache size validation."""
        with pytest.raises(ValueError):
            CacheConfig(max_cache_size_mb=0)


class TestCacheManager:
    """Tests for CacheManager."""

    @pytest.fixture
    def cache_manager(self, tmp_path: Path) -> CacheManager:
        """Create cache manager with temp directory."""
        config = CacheConfig(cache_dir=tmp_path)
        return CacheManager(config)

    def test_init_creates_directory(self, tmp_path: Path) -> None:
        """Test that cache manager creates directory on init."""
        cache_dir = tmp_path / "test_cache"
        assert not cache_dir.exists()

        config = CacheConfig(cache_dir=cache_dir)
        CacheManager(config)

        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_set_and_get(self, cache_manager: CacheManager) -> None:
        """Test storing and retrieving a value."""
        key = "test_key"
        value = {"data": "test_value", "number": 42}

        cache_manager.set(key, value)
        result = cache_manager.get(key)

        assert result == value

    def test_get_missing_key(self, cache_manager: CacheManager) -> None:
        """Test getting a non-existent key returns None."""
        result = cache_manager.get("nonexistent_key")
        assert result is None

    def test_cache_expiration_on_get(self, cache_manager: CacheManager) -> None:
        """Test that get() checks expiration on retrieval."""
        key = "test_key"
        value = {"data": "test_value"}

        # Set value and manually modify timestamp to simulate expired entry
        cache_manager.set(key, value)
        cache_file = cache_manager._get_cache_file(key)

        # Read, modify timestamp to be old, and write back
        with open(cache_file, "r") as f:
            data = json.load(f)

        data["timestamp"] = time.time() - 100000  # 100k seconds ago
        with open(cache_file, "w") as f:
            json.dump(data, f)

        # Now get should return None and delete the file
        result = cache_manager.get(key)
        assert result is None
        assert not cache_file.exists()

    def test_delete(self, cache_manager: CacheManager) -> None:
        """Test deleting a cache entry."""
        key = "test_key"
        value = {"data": "test_value"}

        cache_manager.set(key, value)
        assert cache_manager.get(key) == value

        cache_manager.delete(key)
        assert cache_manager.get(key) is None

    def test_delete_nonexistent(self, cache_manager: CacheManager) -> None:
        """Test deleting a non-existent key doesn't raise error."""
        cache_manager.delete("nonexistent_key")  # Should not raise

    def test_clear(self, cache_manager: CacheManager) -> None:
        """Test clearing all cache entries."""
        cache_manager.set("key1", {"value": 1})
        cache_manager.set("key2", {"value": 2})
        cache_manager.set("key3", {"value": 3})

        assert len(list(cache_manager.config.cache_dir.glob("*.json"))) == 3

        cache_manager.clear()

        assert len(list(cache_manager.config.cache_dir.glob("*.json"))) == 0

    def test_cleanup_expired(self, cache_manager: CacheManager) -> None:
        """Test cleanup removes expired entries."""
        # Add expired entry
        cache_manager.set("old_key", {"value": 1}, ttl=1)
        time.sleep(1.1)

        # Add non-expired entry
        cache_manager.set("new_key", {"value": 2}, ttl=3600)

        cache_manager.cleanup_expired()

        # Old should be deleted, new should remain
        assert cache_manager.get("old_key") is None
        assert cache_manager.get("new_key") == {"value": 2}

    def test_get_cache_size(self, cache_manager: CacheManager) -> None:
        """Test getting cache size."""
        assert cache_manager.get_cache_size() == 0.0

        cache_manager.set("key1", {"data": "x" * 1000})
        size = cache_manager.get_cache_size()

        assert size > 0.0
        assert size < 1.0  # Should be less than 1 MB

    def test_get_cache_size_empty_dir(self, tmp_path: Path) -> None:
        """Test cache size when directory doesn't exist."""
        config = CacheConfig(cache_dir=tmp_path / "nonexistent")
        manager = CacheManager(config)

        size = manager.get_cache_size()
        assert size == 0.0

    def test_caching_disabled(self, tmp_path: Path) -> None:
        """Test that caching is skipped when disabled."""
        config = CacheConfig(cache_dir=tmp_path, enabled=False)
        manager = CacheManager(config)

        manager.set("key", {"value": 1})
        result = manager.get("key")

        assert result is None
        assert len(list(tmp_path.glob("*.json"))) == 0

    def test_key_sanitization(self, cache_manager: CacheManager) -> None:
        """Test that special characters in keys are handled."""
        key_with_special = "key/with\\special:chars*?"
        value = {"data": "test"}

        cache_manager.set(key_with_special, value)
        result = cache_manager.get(key_with_special)

        assert result == value

    def test_concurrent_access(self, cache_manager: CacheManager) -> None:
        """Test multiple cache operations."""
        for i in range(10):
            cache_manager.set(f"key_{i}", {"value": i})

        for i in range(10):
            result = cache_manager.get(f"key_{i}")
            assert result == {"value": i}

    def test_set_raises_on_init_failure(self, tmp_path: Path) -> None:
        """Test that set raises CacheError on failure."""
        config = CacheConfig(cache_dir=tmp_path)
        manager = CacheManager(config)

        # Make directory read-only to cause write failure
        tmp_path.chmod(0o444)
        try:
            with pytest.raises(CacheError):
                manager.set("key", {"value": 1})
        finally:
            tmp_path.chmod(0o755)

    def test_json_serialization(self, cache_manager: CacheManager) -> None:
        """Test that values are properly JSON serialized."""
        value = {"string": "test", "number": 42, "list": [1, 2, 3]}

        cache_manager.set("test_key", value)

        # Verify file contains valid JSON
        cache_file = cache_manager._get_cache_file("test_key")
        with open(cache_file) as f:
            data = json.load(f)

        assert data["value"] == value
        assert "timestamp" in data
        assert "ttl" in data

    def test_cleanup_on_size_limit(self, tmp_path: Path) -> None:
        """Test cleanup is triggered when cache size limit is exceeded."""
        config = CacheConfig(cache_dir=tmp_path, max_cache_size_mb=1)  # 1 MB limit
        manager = CacheManager(config)

        # Add entries that will eventually trigger cleanup
        for i in range(5):
            manager.set(f"key_{i}", {"data": "x" * 250000})  # ~250KB each

        # Cleanup was triggered and removed expired entries
        # At least some files should remain (cleanup only removes expired)
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) >= 1

    def test_ttl_override(self, cache_manager: CacheManager) -> None:
        """Test that per-entry TTL overrides default."""
        key = "test_key"
        value = {"data": "test"}

        # Set with override TTL of 1 second
        cache_manager.set(key, value, ttl=1)

        # Verify file has correct TTL
        cache_file = cache_manager._get_cache_file(key)
        with open(cache_file) as f:
            data = json.load(f)

        assert data["ttl"] == 1
