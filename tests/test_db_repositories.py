"""Tests for database repository classes."""

from __future__ import annotations

from pathlib import Path

import pytest

from unrealitytv.db import Database, EpisodeRepository, RepositoryError, SkipSegmentRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Create temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def db(db_path: Path) -> Database:
    """Initialize database with migrations."""
    database = Database(db_path)
    database.initialize()
    return database


@pytest.fixture
def episode_repo(db: Database) -> EpisodeRepository:
    """Create episode repository."""
    return EpisodeRepository(db)


@pytest.fixture
def segment_repo(db: Database) -> SkipSegmentRepository:
    """Create skip segment repository."""
    return SkipSegmentRepository(db)


class TestEpisodeRepository:
    """Tests for EpisodeRepository class."""

    def test_add_episode_success(self, episode_repo: EpisodeRepository) -> None:
        """Test adding a valid episode."""
        episode_id = episode_repo.add_episode(
            file_path="test.mp4",
            show_name="Test Show",
            season=1,
            episode=1,
            duration_ms=3600000,
        )
        assert isinstance(episode_id, int)
        assert episode_id > 0

    def test_add_episode_minimal(self, episode_repo: EpisodeRepository) -> None:
        """Test adding episode with minimal fields."""
        episode_id = episode_repo.add_episode(
            file_path="minimal.mp4",
            show_name="Minimal Show",
        )
        assert isinstance(episode_id, int)
        assert episode_id > 0

    def test_add_episode_duplicate(self, episode_repo: EpisodeRepository) -> None:
        """Test duplicate file path raises error."""
        episode_repo.add_episode("duplicate.mp4", "Show A")
        with pytest.raises(RepositoryError, match="already exists"):
            episode_repo.add_episode("duplicate.mp4", "Show B")

    def test_update_episode_metadata(
        self, episode_repo: EpisodeRepository
    ) -> None:
        """Test updating episode metadata."""
        episode_id = episode_repo.add_episode("update.mp4", "Update Show")
        episode_repo.update_episode_metadata(
            episode_id, duration_ms=5400000, analyzed_at="2024-02-12T00:00:00Z"
        )
        episode = episode_repo.get_episode_by_file_path("update.mp4")
        assert episode["duration_ms"] == 5400000
        assert episode["analyzed_at"] == "2024-02-12T00:00:00Z"

    def test_update_episode_not_found(
        self, episode_repo: EpisodeRepository
    ) -> None:
        """Test updating non-existent episode raises error."""
        with pytest.raises(RepositoryError, match="No episode found"):
            episode_repo.update_episode_metadata(999, duration_ms=1000)

    def test_get_episode_by_file_path_success(
        self, episode_repo: EpisodeRepository
    ) -> None:
        """Test retrieving episode by file path."""
        episode_id = episode_repo.add_episode(
            "get_test.mp4", "Get Show", season=2, episode=5
        )
        episode = episode_repo.get_episode_by_file_path("get_test.mp4")
        assert episode is not None
        assert episode["id"] == episode_id
        assert episode["show_name"] == "Get Show"
        assert episode["season"] == 2
        assert episode["episode"] == 5

    def test_get_episode_by_file_path_not_found(
        self, episode_repo: EpisodeRepository
    ) -> None:
        """Test retrieving non-existent episode returns None."""
        episode = episode_repo.get_episode_by_file_path("nonexistent.mp4")
        assert episode is None

    def test_find_episodes_by_show(self, episode_repo: EpisodeRepository) -> None:
        """Test finding all episodes of a show."""
        episode_repo.add_episode("show1_ep1.mp4", "Show 1", season=1, episode=1)
        episode_repo.add_episode("show1_ep2.mp4", "Show 1", season=1, episode=2)
        episode_repo.add_episode("show2_ep1.mp4", "Show 2", season=1, episode=1)

        show1_episodes = episode_repo.find_episodes_by_show("Show 1")
        assert len(show1_episodes) == 2
        assert all(ep["show_name"] == "Show 1" for ep in show1_episodes)

    def test_find_episodes_by_show_empty(self, episode_repo: EpisodeRepository) -> None:
        """Test finding episodes for non-existent show returns empty list."""
        episodes = episode_repo.find_episodes_by_show("Nonexistent Show")
        assert episodes == []

    def test_find_episodes_by_season(
        self, episode_repo: EpisodeRepository
    ) -> None:
        """Test finding episodes by show and season."""
        episode_repo.add_episode("show_s1_e1.mp4", "Show", season=1, episode=1)
        episode_repo.add_episode("show_s1_e2.mp4", "Show", season=1, episode=2)
        episode_repo.add_episode("show_s2_e1.mp4", "Show", season=2, episode=1)

        season1_episodes = episode_repo.find_episodes_by_season("Show", 1)
        assert len(season1_episodes) == 2
        assert all(ep["season"] == 1 for ep in season1_episodes)

    def test_find_episodes_by_season_empty(
        self, episode_repo: EpisodeRepository
    ) -> None:
        """Test finding episodes for non-existent season returns empty list."""
        episode_repo.add_episode("show_s1_e1.mp4", "Show", season=1)
        episodes = episode_repo.find_episodes_by_season("Show", 99)
        assert episodes == []

    def test_delete_episode_success(self, episode_repo: EpisodeRepository) -> None:
        """Test deleting an existing episode."""
        episode_id = episode_repo.add_episode("delete.mp4", "Delete Show")
        episode_repo.delete_episode(episode_id)
        episode = episode_repo.get_episode_by_file_path("delete.mp4")
        assert episode is None

    def test_delete_episode_not_found(self, episode_repo: EpisodeRepository) -> None:
        """Test deleting non-existent episode raises error."""
        with pytest.raises(RepositoryError, match="No episode found"):
            episode_repo.delete_episode(999)


class TestSkipSegmentRepository:
    """Tests for SkipSegmentRepository class."""

    def test_add_segment_success(
        self, db: Database, episode_repo: EpisodeRepository,
        segment_repo: SkipSegmentRepository
    ) -> None:
        """Test adding a valid skip segment."""
        episode_id = episode_repo.add_episode("ep1.mp4", "Show")
        segment_id = segment_repo.add_segment(
            episode_id=episode_id,
            start_ms=1000,
            end_ms=5000,
            segment_type="recap",
            confidence=0.95,
        )
        assert isinstance(segment_id, int)
        assert segment_id > 0

    def test_add_segment_with_reason(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test adding segment with reason field."""
        episode_id = episode_repo.add_episode("ep2.mp4", "Show")
        segment_id = segment_repo.add_segment(
            episode_id=episode_id,
            start_ms=1000,
            end_ms=5000,
            segment_type="preview",
            confidence=0.85,
            reason="Detected: coming up next",
        )
        assert isinstance(segment_id, int)

    def test_get_segments_by_episode(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test retrieving all segments for an episode."""
        episode_id = episode_repo.add_episode("ep3.mp4", "Show")
        segment_repo.add_segment(episode_id, 1000, 5000, "recap", 0.95)
        segment_repo.add_segment(episode_id, 50000, 55000, "preview", 0.85)

        segments = segment_repo.get_segments_by_episode(episode_id)
        assert len(segments) == 2
        assert all(seg["episode_id"] == episode_id for seg in segments)

    def test_get_segments_by_episode_empty(
        self, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test retrieving segments for episode with none returns empty list."""
        segments = segment_repo.get_segments_by_episode(999)
        assert segments == []

    def test_update_segment(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test updating a skip segment."""
        episode_id = episode_repo.add_episode("ep4.mp4", "Show")
        segment_id = segment_repo.add_segment(
            episode_id, 1000, 5000, "recap", 0.90, "Old reason"
        )

        segment_repo.update_segment(
            segment_id, 2000, 6000, 0.98, "New reason"
        )

        segments = segment_repo.get_segments_by_episode(episode_id)
        updated = segments[0]
        assert updated["start_ms"] == 2000
        assert updated["end_ms"] == 6000
        assert updated["confidence"] == 0.98
        assert updated["reason"] == "New reason"

    def test_update_segment_not_found(
        self, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test updating non-existent segment raises error."""
        with pytest.raises(RepositoryError, match="No segment found"):
            segment_repo.update_segment(999, 1000, 5000, 0.95)

    def test_delete_segment(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test deleting a segment."""
        episode_id = episode_repo.add_episode("ep5.mp4", "Show")
        segment_id = segment_repo.add_segment(episode_id, 1000, 5000, "recap", 0.95)

        segment_repo.delete_segment(segment_id)

        segments = segment_repo.get_segments_by_episode(episode_id)
        assert len(segments) == 0

    def test_delete_segment_not_found(
        self, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test deleting non-existent segment raises error."""
        with pytest.raises(RepositoryError, match="No segment found"):
            segment_repo.delete_segment(999)

    def test_delete_segments_by_episode(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test deleting all segments for an episode."""
        episode_id = episode_repo.add_episode("ep6.mp4", "Show")
        segment_repo.add_segment(episode_id, 1000, 5000, "recap", 0.95)
        segment_repo.add_segment(episode_id, 50000, 55000, "preview", 0.85)

        deleted_count = segment_repo.delete_segments_by_episode(episode_id)
        assert deleted_count == 2

        segments = segment_repo.get_segments_by_episode(episode_id)
        assert len(segments) == 0

    def test_delete_segments_by_episode_none(
        self, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test deleting segments for episode with none returns 0."""
        deleted_count = segment_repo.delete_segments_by_episode(999)
        assert deleted_count == 0


class TestIntegration:
    """Integration tests for repositories."""

    def test_episode_and_segments_together(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test adding episode and segments together."""
        episode_id = episode_repo.add_episode(
            "integration.mp4", "Integration Show", season=1, episode=1
        )

        segment_repo.add_segment(episode_id, 1000, 5000, "recap", 0.95, "Previously...")
        segment_repo.add_segment(episode_id, 50000, 55000, "preview", 0.85, "Coming up...")

        # Verify episode
        episode = episode_repo.get_episode_by_file_path("integration.mp4")
        assert episode["show_name"] == "Integration Show"

        # Verify segments
        segments = segment_repo.get_segments_by_episode(episode_id)
        assert len(segments) == 2
        assert segments[0]["segment_type"] == "recap"
        assert segments[1]["segment_type"] == "preview"

    def test_multiple_episodes_and_segments(
        self, episode_repo: EpisodeRepository, segment_repo: SkipSegmentRepository
    ) -> None:
        """Test handling multiple episodes with segments."""
        ep1_id = episode_repo.add_episode("multi1.mp4", "Multi Show", season=1, episode=1)
        ep2_id = episode_repo.add_episode("multi2.mp4", "Multi Show", season=1, episode=2)

        # Add segments to both
        segment_repo.add_segment(ep1_id, 1000, 5000, "recap", 0.95)
        segment_repo.add_segment(ep2_id, 2000, 6000, "recap", 0.92)

        # Verify episodes
        episodes = episode_repo.find_episodes_by_show("Multi Show")
        assert len(episodes) == 2

        # Verify segments are isolated
        seg1 = segment_repo.get_segments_by_episode(ep1_id)
        seg2 = segment_repo.get_segments_by_episode(ep2_id)
        assert len(seg1) == 1
        assert len(seg2) == 1
        assert seg1[0]["start_ms"] == 1000
        assert seg2[0]["start_ms"] == 2000
