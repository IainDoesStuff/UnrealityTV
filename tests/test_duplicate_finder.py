"""Tests for cross-episode duplicate finder."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unrealitytv.db import Database
from unrealitytv.visual.duplicate_finder import DuplicateFinder


@pytest.fixture
def mock_db():
    """Create a mock database instance."""
    db = MagicMock(spec=Database)
    db.connection = MagicMock()
    return db


@pytest.fixture
def finder(mock_db):
    """Create a DuplicateFinder instance."""
    return DuplicateFinder(mock_db, hamming_threshold=8)


class TestDuplicateFinderFindDuplicates:
    """Tests for find_duplicates method."""

    def test_find_duplicates_exact_match(self, finder, mock_db):
        """Test finding exact duplicate matches."""
        # Mock is set up via fixture

        # Create mock repo return values
        source_hashes = [
            {"id": 1, "episode_id": 1, "timestamp_ms": 0, "phash": "aaaa"},
            {"id": 2, "episode_id": 1, "timestamp_ms": 1000, "phash": "bbbb"},
        ]

        # Mock similar hashes (exact match)
        match_hash = {"id": 3, "episode_id": 2, "timestamp_ms": 0, "phash": "aaaa"}

        with patch(
            "unrealitytv.db.FrameHashRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_hashes_by_episode.return_value = source_hashes
            mock_repo.find_similar_hashes.side_effect = [
                [match_hash],  # Match for first hash
                [],  # No match for second hash
            ]

            matches = finder.find_duplicates(1)

            assert len(matches) == 1
            assert matches[0].source_episode_id == 1
            assert matches[0].match_episode_id == 2
            assert matches[0].hamming_distance == 0

    def test_find_duplicates_near_match(self, finder, mock_db):
        """Test finding near-match duplicates within threshold."""
        source_hashes = [
            {"id": 1, "episode_id": 1, "timestamp_ms": 0, "phash": "aaaaaaaaaaaaaaaa"},
        ]
        match_hash = {
            "id": 2,
            "episode_id": 2,
            "timestamp_ms": 0,
            "phash": "aaaaaaaaaaaaaaba",
        }  # 1 bit different

        with patch(
            "unrealitytv.db.FrameHashRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_hashes_by_episode.return_value = source_hashes
            mock_repo.find_similar_hashes.return_value = [match_hash]

            matches = finder.find_duplicates(1)

            assert len(matches) == 1
            assert matches[0].hamming_distance == 1

    def test_find_duplicates_outside_threshold(self, finder, mock_db):
        """Test that matches outside threshold are excluded."""
        finder.hamming_threshold = 3
        source_hashes = [
            {"id": 1, "episode_id": 1, "timestamp_ms": 0, "phash": "0000000000000000"},
        ]
        # Create a hash with 5 bits different (ff has 8 bits, but we XOR one byte)
        # 0x00 XOR 0x1f = 0x1f (00011111 = 5 bits)
        match_hash = {
            "id": 2,
            "episode_id": 2,
            "timestamp_ms": 0,
            "phash": "000000001f000000",
        }  # 5 bits different

        with patch(
            "unrealitytv.db.FrameHashRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_hashes_by_episode.return_value = source_hashes
            mock_repo.find_similar_hashes.return_value = [match_hash]

            matches = finder.find_duplicates(1)

            assert len(matches) == 0

    def test_find_duplicates_empty_result(self, finder, mock_db):
        """Test with no duplicates found."""
        with patch(
            "unrealitytv.db.FrameHashRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_hashes_by_episode.return_value = []

            matches = finder.find_duplicates(999)

            assert matches == []

    def test_find_duplicates_sorted_by_timestamp(self, finder, mock_db):
        """Test that results are sorted by source_timestamp_ms."""
        source_hashes = [
            {"id": 1, "episode_id": 1, "timestamp_ms": 5000, "phash": "aaaa"},
            {"id": 2, "episode_id": 1, "timestamp_ms": 1000, "phash": "bbbb"},
            {"id": 3, "episode_id": 1, "timestamp_ms": 3000, "phash": "cccc"},
        ]
        match_hash = {"id": 4, "episode_id": 2, "timestamp_ms": 0, "phash": "aaaa"}

        with patch(
            "unrealitytv.db.FrameHashRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_hashes_by_episode.return_value = source_hashes
            mock_repo.find_similar_hashes.side_effect = [
                [match_hash],
                [],
                [],
            ]

            matches = finder.find_duplicates(1)

            assert len(matches) == 1
            assert matches[0].source_timestamp_ms == 5000


class TestDuplicateFinderFindDuplicatesForHashes:
    """Tests for find_duplicates_for_hashes method."""

    def test_find_duplicates_for_hashes_basic(self, finder, mock_db):
        """Test finding duplicates for provided hashes."""
        hashes = [(0, "aaaa"), (1000, "bbbb")]
        match_hash = {"id": 1, "episode_id": 2, "timestamp_ms": 0, "phash": "aaaa"}

        with patch(
            "unrealitytv.db.FrameHashRepository"
        ) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.find_similar_hashes.side_effect = [
                [match_hash],
                [],
            ]

            matches = finder.find_duplicates_for_hashes(1, hashes)

            assert len(matches) == 1
            assert matches[0].source_timestamp_ms == 0


class TestHammingDistance:
    """Tests for _hamming_distance static method."""

    def test_hamming_distance_identical(self):
        """Test distance for identical hashes."""
        assert DuplicateFinder._hamming_distance("aaaa", "aaaa") == 0

    def test_hamming_distance_one_bit(self):
        """Test distance with one bit difference."""
        # 0xa XOR 0xb = 0x1 (1 bit set)
        assert DuplicateFinder._hamming_distance("000a", "000b") == 1

    def test_hamming_distance_all_different(self):
        """Test distance for completely different hashes."""
        assert DuplicateFinder._hamming_distance("0000", "ffff") == 16

    def test_hamming_distance_invalid_hex(self):
        """Test with invalid hex string returns max distance."""
        distance = DuplicateFinder._hamming_distance("zzzz", "aaaa")
        assert distance == 64
