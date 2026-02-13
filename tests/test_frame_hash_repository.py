"""Tests for frame hash repository."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unrealitytv.db import Database, FrameHashRepository, RepositoryError


@pytest.fixture
def mock_db():
    """Create a mock database instance."""
    db = MagicMock(spec=Database)
    db.connection = MagicMock()
    return db


@pytest.fixture
def repo(mock_db):
    """Create a repository instance with mock database."""
    return FrameHashRepository(mock_db)


class TestFrameHashRepositoryAddHashesBatch:
    """Tests for add_hashes_batch method."""

    def test_add_hashes_batch_success(self, repo, mock_db):
        """Test successful batch insert of hashes."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 3
        mock_db.connection.cursor.return_value = mock_cursor

        hashes = [(0, "aaaaaaaaaaaaaaaa"), (1000, "bbbbbbbbbbbbbbbb")]
        result = repo.add_hashes_batch(1, hashes)

        assert result == 3
        mock_cursor.executemany.assert_called_once()
        mock_db.connection.commit.assert_called_once()

    def test_add_hashes_batch_failure(self, repo, mock_db):
        """Test RepositoryError on insert failure."""
        mock_cursor = MagicMock()
        mock_cursor.executemany.side_effect = Exception("Insert failed")
        mock_db.connection.cursor.return_value = mock_cursor

        with pytest.raises(RepositoryError) as exc_info:
            repo.add_hashes_batch(1, [(0, "hash")])

        assert "Failed to add frame hashes" in str(exc_info.value)


class TestFrameHashRepositoryGetHashesByEpisode:
    """Tests for get_hashes_by_episode method."""

    def test_get_hashes_by_episode_success(self, repo, mock_db):
        """Test retrieving hashes for an episode."""
        mock_cursor = MagicMock()
        mock_row1 = MagicMock()
        mock_row1.__getitem__ = lambda self, key: {0: 1, "id": 1, "episode_id": 1, "timestamp_ms": 0, "phash": "aaaa"}[key]
        mock_row2 = MagicMock()
        mock_row2.__getitem__ = lambda self, key: {0: 2, "id": 2, "episode_id": 1, "timestamp_ms": 1000, "phash": "bbbb"}[key]

        mock_cursor.fetchall.return_value = [mock_row1, mock_row2]
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.get_hashes_by_episode(1)

        assert len(result) == 2
        mock_cursor.execute.assert_called_once()
        assert "ORDER BY timestamp_ms ASC" in mock_cursor.execute.call_args[0][0]

    def test_get_hashes_by_episode_empty(self, repo, mock_db):
        """Test retrieving hashes when none exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.get_hashes_by_episode(999)

        assert result == []

    def test_get_hashes_by_episode_failure(self, repo, mock_db):
        """Test RepositoryError on query failure."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query failed")
        mock_db.connection.cursor.return_value = mock_cursor

        with pytest.raises(RepositoryError) as exc_info:
            repo.get_hashes_by_episode(1)

        assert "Failed to get hashes by episode" in str(exc_info.value)


class TestFrameHashRepositoryFindSimilarHashes:
    """Tests for find_similar_hashes method."""

    def test_find_similar_hashes_with_exclusion(self, repo, mock_db):
        """Test finding similar hashes excluding specific episode."""
        mock_cursor = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {0: 1, "id": 1, "episode_id": 2, "timestamp_ms": 0, "phash": "aaaa"}[key]
        mock_cursor.fetchall.return_value = [mock_row]
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.find_similar_hashes("aaaa", exclude_episode_id=1)

        assert len(result) == 1
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "episode_id !=" in call_args[0]

    def test_find_similar_hashes_without_exclusion(self, repo, mock_db):
        """Test finding similar hashes without exclusion."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.find_similar_hashes("aaaa")

        assert result == []
        call_args = mock_cursor.execute.call_args[0]
        assert "episode_id !=" not in call_args[0]

    def test_find_similar_hashes_failure(self, repo, mock_db):
        """Test RepositoryError on query failure."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Query failed")
        mock_db.connection.cursor.return_value = mock_cursor

        with pytest.raises(RepositoryError) as exc_info:
            repo.find_similar_hashes("aaaa")

        assert "Failed to find similar hashes" in str(exc_info.value)


class TestFrameHashRepositoryDeleteHashesByEpisode:
    """Tests for delete_hashes_by_episode method."""

    def test_delete_hashes_by_episode_success(self, repo, mock_db):
        """Test successful deletion of hashes."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 5
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.delete_hashes_by_episode(1)

        assert result == 5
        mock_cursor.execute.assert_called_once()
        mock_db.connection.commit.assert_called_once()

    def test_delete_hashes_by_episode_none(self, repo, mock_db):
        """Test deletion when no hashes exist."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.delete_hashes_by_episode(999)

        assert result == 0

    def test_delete_hashes_by_episode_failure(self, repo, mock_db):
        """Test RepositoryError on deletion failure."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Delete failed")
        mock_db.connection.cursor.return_value = mock_cursor

        with pytest.raises(RepositoryError) as exc_info:
            repo.delete_hashes_by_episode(1)

        assert "Failed to delete hashes by episode" in str(exc_info.value)


class TestFrameHashRepositoryGetHashCount:
    """Tests for get_hash_count method."""

    def test_get_hash_count_for_episode(self, repo, mock_db):
        """Test counting hashes for specific episode."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (10,)
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.get_hash_count(episode_id=1)

        assert result == 10
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE episode_id = ?" in call_args[0]

    def test_get_hash_count_all(self, repo, mock_db):
        """Test counting all hashes."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.get_hash_count()

        assert result == 100
        call_args = mock_cursor.execute.call_args[0]
        assert "WHERE" not in call_args[0]

    def test_get_hash_count_zero(self, repo, mock_db):
        """Test count when no hashes exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.get_hash_count(episode_id=999)

        assert result == 0

    def test_get_hash_count_none_result(self, repo, mock_db):
        """Test count when fetchone returns None."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.connection.cursor.return_value = mock_cursor

        result = repo.get_hash_count()

        assert result == 0

    def test_get_hash_count_failure(self, repo, mock_db):
        """Test RepositoryError on count failure."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Count failed")
        mock_db.connection.cursor.return_value = mock_cursor

        with pytest.raises(RepositoryError) as exc_info:
            repo.get_hash_count()

        assert "Failed to get hash count" in str(exc_info.value)


class TestFrameHashRepositoryRoundTrip:
    """Integration tests for round-trip operations."""

    def test_round_trip_add_and_get(self, repo, mock_db):
        """Test adding and retrieving hashes."""
        # Setup mocks for add
        add_cursor = MagicMock()
        add_cursor.rowcount = 2

        # Setup mocks for get
        get_cursor = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            "id": 1,
            "episode_id": 1,
            "timestamp_ms": 0,
            "phash": "aaaa",
        }[key]
        get_cursor.fetchall.return_value = [mock_row]

        mock_db.connection.cursor.side_effect = [add_cursor, get_cursor]

        hashes = [(0, "aaaa")]
        add_count = repo.add_hashes_batch(1, hashes)
        assert add_count == 2

        retrieved = repo.get_hashes_by_episode(1)
        assert len(retrieved) == 1
